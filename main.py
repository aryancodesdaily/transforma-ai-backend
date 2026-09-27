import asyncio
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from ai_engine import generate_content
from config import ALLOWED_ORIGINS
from hashing import hash_content
from input_processor import process_file, process_text
from instructions import SYSTEM_INSTRUCTION, build_transformation_prompt
from mongodb_service import store_transformation
from output_generator import generate_output

app = FastAPI(
    title="AI Content Transformation Platform",
    description="AI-powered platform for transforming source content into requested communication artefacts.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*ALLOWED_ORIGINS],
    allow_origin_regex=r"^https://[a-z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Limit of 5 transformations per hour reached. Try again later."},
    )

MEDIA_TYPES = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "PNG": "image/png",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_TEXT_LENGTH = 100_000
MAX_OUTPUTS_PER_REQUEST = 3
MAX_CONCURRENT_GENERATIONS = 3

generation_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)
OUTPUT_DIR = Path("generated_outputs")


@app.get("/")
def root():
    return {"message": "AI Content Transformation API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def build_source_content(source_text: str, file: Optional[UploadFile]) -> str:
    if len(source_text) > MAX_SOURCE_TEXT_LENGTH:
        raise HTTPException(status_code=413, detail="Source text is too large.")

    if source_text.strip():
        return process_text(source_text)

    if file is None:
        raise HTTPException(
            status_code=400,
            detail="Please provide source text or upload a file.",
        )

    file_extension = Path(file.filename).suffix.lower()
    file_content = file.file.read()

    if len(file_content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"'{file.filename}' exceeds the 10 MB upload limit.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    try:
        return process_file(temp_file_path)
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=f"Could not process '{file.filename}': {error}",
        )
    finally:
        Path(temp_file_path).unlink(missing_ok=True)


async def generate_single_output(
    output: dict,
    combined_source_content: str,
    additional_instructions: str,
    input_hash: str,
) -> Path:
    async with generation_semaphore:
        prompt = build_transformation_prompt(
            source_content=combined_source_content,
            audience=output["audience"],
            objective=output["objective"],
            tone=output["tone"],
            language=output["language"],
            detail_level=output["detail_level"],
            content_style=output["content_style"],
            output_type=output["output_type"],
            additional_instructions=additional_instructions,
        )

        generated_content = await asyncio.to_thread(
            generate_content, SYSTEM_INSTRUCTION, prompt
        )

        output_format = output["output_format"]
        file_extension = output_format.lower()
        output_file_path = OUTPUT_DIR / f"{uuid4().hex}.{file_extension}"

        await asyncio.to_thread(
            generate_output,
            content=generated_content,
            output_format=output_format,
            output_path=str(output_file_path),
        )

        try:
            output_hash = hash_content(generated_content)
            await asyncio.to_thread(
                store_transformation,
                input_hash=input_hash,
                output_hash=output_hash,
                transformation_details={
                    "audience": output["audience"],
                    "objective": output["objective"],
                    "tone": output["tone"],
                    "language": output["language"],
                    "detail_level": output["detail_level"],
                    "content_style": output["content_style"],
                    "output_type": output["output_type"],
                    "output_format": output_format,
                    "additional_instructions": additional_instructions,
                },
            )
        except Exception as error:
            print(f"Warning: could not store transformation record: {error}")

        return output_file_path


@app.post("/transform")
@limiter.limit("5/hour")
async def transform_content(
    request: Request,
    background_tasks: BackgroundTasks,
    source_text: str = Form(""),
    file: Optional[UploadFile] = File(None),
    additional_instructions: str = Form(""),
    outputs: str = Form(...),
):
    combined_source_content = build_source_content(source_text, file)
    input_hash = hash_content(combined_source_content)

    try:
        output_list = json.loads(outputs)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="'outputs' must be valid JSON.")

    if not output_list:
        raise HTTPException(status_code=400, detail="At least one output is required.")

    if len(output_list) > MAX_OUTPUTS_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=f"A maximum of {MAX_OUTPUTS_PER_REQUEST} outputs can be requested at once.",
        )

    OUTPUT_DIR.mkdir(exist_ok=True)

    try:
        generated_paths = await asyncio.gather(*[
            generate_single_output(output, combined_source_content, additional_instructions, input_hash)
            for output in output_list
        ])
    except ValueError as error:
        raise HTTPException(status_code=422, detail=f"Generation failed: {error}")

    for path in generated_paths:
        background_tasks.add_task(path.unlink, missing_ok=True)

    if len(generated_paths) == 1:
        single_path = generated_paths[0]
        file_extension = single_path.suffix.lstrip(".")

        return FileResponse(
            path=str(single_path),
            filename=f"transformed_content.{file_extension}",
            media_type=MEDIA_TYPES.get(file_extension.upper(), "application/octet-stream"),
            background=background_tasks,
        )

    zip_path = OUTPUT_DIR / f"{uuid4().hex}.zip"

    with zipfile.ZipFile(zip_path, "w") as zip_file:
        for index, path in enumerate(generated_paths, start=1):
            file_extension = path.suffix.lstrip(".")
            zip_file.write(path, arcname=f"output_{index}.{file_extension}")

    background_tasks.add_task(zip_path.unlink, missing_ok=True)

    return FileResponse(
        path=str(zip_path),
        filename="transformed_outputs.zip",
        media_type="application/zip",
        background=background_tasks,
    )






# from instructions import SYSTEM_INSTRUCTION, build_transformation_prompt
# from ai_engine import generate_content
# from output_generator import generate_output
# from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import FileResponse
# from typing import List
# import tempfile
# from pathlib import Path
# from uuid import uuid4

# from config import ALLOWED_ORIGINS
# from input_processor import process_file, process_text

# from hashing import hash_content
# from mongodb_service import store_transformation


# app = FastAPI(
#     title="AI Content Transformation Platform",
#     description="AI-powered platform for transforming source content into requested communication artefacts.",
#     version="1.0.0"
# )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         *ALLOWED_ORIGINS,
#     ],
#     allow_origin_regex=r"^https://[a-z0-9-]+\.vercel\.app$",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# MEDIA_TYPES = {
#     "PDF": "application/pdf",
#     "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#     "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
#     "PNG": "image/png",
# }

# MAX_FILES = 5
# MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
# MAX_SOURCE_TEXT_LENGTH = 100_000


# @app.get("/")
# def root():
#     return {"message": "AI Content Transformation API is running"}


# @app.get("/health")
# def health_check():
#     return {"status": "healthy"}


# @app.post("/transform")
# def transform_content(
#     background_tasks: BackgroundTasks,
#     source_text: str = Form(""),
#     files: List[UploadFile] = File(default=[]),

#     audience: str = Form(...),
#     objective: str = Form(...),
#     tone: str = Form(...),
#     language: str = Form(...),
#     detail_level: str = Form(...),
#     content_style: str = Form(...),
#     output_type: str = Form(...),
#     output_format: str = Form(...),
#     additional_instructions: str = Form("")
# ):
#     extracted_contents = []

#     if len(files) > MAX_FILES:
#         raise HTTPException(
#             status_code=413,
#             detail=f"A maximum of {MAX_FILES} files can be uploaded at once.",
#         )

#     if len(source_text) > MAX_SOURCE_TEXT_LENGTH:
#         raise HTTPException(
#             status_code=413,
#             detail="Source text is too large.",
#         )

#     if source_text.strip():
#         extracted_contents.append(process_text(source_text))

#     for uploaded_file in files:
#         file_extension = Path(uploaded_file.filename).suffix.lower()
#         file_content = uploaded_file.file.read()

#         if len(file_content) > MAX_FILE_SIZE_BYTES:
#             raise HTTPException(
#                 status_code=413,
#                 detail=f"'{uploaded_file.filename}' exceeds the 10 MB upload limit.",
#             )

#         with tempfile.NamedTemporaryFile(
#             delete=False,
#             suffix=file_extension
#         ) as temp_file:
#             temp_file.write(file_content)
#             temp_file_path = temp_file.name

#         try:
#             extracted_content = process_file(temp_file_path)
#             extracted_contents.append(
#                 f"===== {uploaded_file.filename} =====\n\n{extracted_content}"
#             )
#         except ValueError as error:
#             return {"error": f"Could not process '{uploaded_file.filename}': {error}"}
#         finally:
#             Path(temp_file_path).unlink(missing_ok=True)

#     if not extracted_contents:
#         return {"error": "Please provide source text or upload at least one file."}

#     combined_source_content = "\n\n".join(extracted_contents)
    
#     input_hash = hash_content(combined_source_content)

#     transformation_prompt = build_transformation_prompt(
#         source_content=combined_source_content,
#         audience=audience,
#         objective=objective,
#         tone=tone,
#         language=language,
#         detail_level=detail_level,
#         content_style=content_style,
#         output_type=output_type,
#         additional_instructions=additional_instructions,
#     )

#     generated_content = generate_content(
#         system_instruction=SYSTEM_INSTRUCTION,
#         user_prompt=transformation_prompt
#     )
    
#     output_hash = hash_content(generated_content)
    
#     transformation_record = store_transformation(
#         input_hash=input_hash,
#         output_hash=output_hash,
#         transformation_details={
#             "audience": audience,
#             "objective": objective,
#             "tone": tone,
#             "language": language,
#             "detail_level": detail_level,
#             "content_style": content_style,
#             "output_type": output_type,
#             "output_format": output_format,
#             "additional_instructions": additional_instructions
#         }
#     )

#     output_directory = Path("generated_outputs")
#     output_directory.mkdir(exist_ok=True)

#     file_extension = output_format.lower()
#     output_file_path = output_directory / f"{uuid4().hex}.{file_extension}"

#     try:
#         generate_output(
#             content=generated_content,
#             output_format=output_format,
#             output_path=str(output_file_path)
#         )
#     except ValueError as error:
#         return {"error": f"Could not generate {output_format} output: {error}"}

#     background_tasks.add_task(output_file_path.unlink, missing_ok=True)

#     return FileResponse(
#         path=str(output_file_path),
#         filename=f"transformed_content.{file_extension}",
#         media_type=MEDIA_TYPES.get(output_format.upper(), "application/octet-stream"),
#         background=background_tasks,
#     )


