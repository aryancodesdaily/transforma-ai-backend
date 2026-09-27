from instructions import SYSTEM_INSTRUCTION, build_transformation_prompt
from ai_engine import generate_content
from output_generator import generate_output
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
import tempfile
from pathlib import Path
from uuid import uuid4

from config import ALLOWED_ORIGINS
from input_processor import process_file, process_text

from hashing import hash_content
from mongodb_service import store_transformation
from mongodb_service import verify_transformation


app = FastAPI(
    title="AI Content Transformation Platform",
    description="AI-powered platform for transforming source content into requested communication artefacts.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *ALLOWED_ORIGINS,
    ],
    allow_origin_regex=r"^https://[a-z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_TYPES = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "PNG": "image/png",
}

MAX_FILES = 5
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_TEXT_LENGTH = 100_000


@app.get("/")
def root():
    return {"message": "AI Content Transformation API is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/transform")
def transform_content(
    background_tasks: BackgroundTasks,
    source_text: str = Form(""),
    files: List[UploadFile] = File(default=[]),

    audience: str = Form(...),
    objective: str = Form(...),
    tone: str = Form(...),
    language: str = Form(...),
    detail_level: str = Form(...),
    content_style: str = Form(...),
    output_type: str = Form(...),
    output_format: str = Form(...),
    additional_instructions: str = Form("")
):
    raw_contents = []
    prompt_contents = []

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"A maximum of {MAX_FILES} files can be uploaded at once.",
        )

    if len(source_text) > MAX_SOURCE_TEXT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail="Source text is too large.",
        )

    if source_text.strip():
        processed_txt = process_text(source_text)
        raw_contents.append(processed_txt)
        prompt_contents.append(processed_txt)

    for uploaded_file in files:
        file_extension = Path(uploaded_file.filename).suffix.lower()
        file_content = uploaded_file.file.read()

        if len(file_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"'{uploaded_file.filename}' exceeds the 10 MB upload limit.",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension
        ) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        try:
            extracted_content = process_file(temp_file_path)
            raw_contents.append(extracted_content)
            prompt_contents.append(
                f"===== {uploaded_file.filename} =====\n\n{extracted_content}"
            )
        except ValueError as error:
            return {"error": f"Could not process '{uploaded_file.filename}': {error}"}
        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    if not raw_contents:
        return {"error": "Please provide source text or upload at least one file."}

    combined_raw_content = "\n\n".join(raw_contents)
    combined_prompt_content = "\n\n".join(prompt_contents)

    input_hash = hash_content(combined_raw_content)

    transformation_prompt = build_transformation_prompt(
        source_content=combined_prompt_content,
        audience=audience,
        objective=objective,
        tone=tone,
        language=language,
        detail_level=detail_level,
        content_style=content_style,
        output_type=output_type,
        additional_instructions=additional_instructions,
    )

    generated_content = generate_content(
        system_instruction=SYSTEM_INSTRUCTION,
        user_prompt=transformation_prompt
    )

    output_directory = Path("generated_outputs")
    output_directory.mkdir(exist_ok=True)

    file_extension = output_format.lower()
    output_file_path = output_directory / f"{uuid4().hex}.{file_extension}"

    try:
        generate_output(
            content=generated_content,
            output_format=output_format,
            output_path=str(output_file_path)
        )
    except ValueError as error:
        return {"error": f"Could not generate {output_format} output: {error}"}

    try:
        extracted_output = process_file(str(output_file_path))
        output_hash = hash_content(extracted_output)
    except Exception:
        output_hash = hash_content(generated_content)

    transformation_record = store_transformation(
        input_hash=input_hash,
        output_hash=output_hash,
        transformation_details={
            "audience": audience,
            "objective": objective,
            "tone": tone,
            "language": language,
            "detail_level": detail_level,
            "content_style": content_style,
            "output_type": output_type,
            "output_format": output_format,
            "additional_instructions": additional_instructions
        }
    )

    background_tasks.add_task(output_file_path.unlink, missing_ok=True)

    return FileResponse(
        path=str(output_file_path),
        filename=f"transformed_content.{file_extension}",
        media_type=MEDIA_TYPES.get(output_format.upper(), "application/octet-stream"),
        background=background_tasks,
    )

@app.post("/verify")
async def verify_files(
    input_file: UploadFile = File(...),
    output_file: UploadFile = File(...)
):
    """
    Verify whether an output was generated from a given input.
    """

    # --------------------------------------------------
    # 1. Save input file temporarily
    # --------------------------------------------------

    input_extension = Path(input_file.filename).suffix.lower()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=input_extension
    ) as temp_input:

        input_content = input_file.file.read()

        if len(input_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"'{input_file.filename}' exceeds the 10 MB upload limit."
            )

        temp_input.write(input_content)
        input_temp_path = temp_input.name

    # --------------------------------------------------
    # 2. Extract input content
    # --------------------------------------------------

    try:
        extracted_input = process_file(input_temp_path)

    except Exception as error:
        return {
            "verdict": "invalid_input_file",
            "message": f"Could not process input file: {error}"
        }

    finally:
        Path(input_temp_path).unlink(missing_ok=True)

    # --------------------------------------------------
    # 3. Generate input hash
    # --------------------------------------------------

    input_hash = hash_content(extracted_input)

    # --------------------------------------------------
    # 4. Save output file temporarily
    # --------------------------------------------------

    output_extension = Path(output_file.filename).suffix.lower()

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=output_extension
    ) as temp_output:

        output_content = await output_file.read()

        if len(output_content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"'{output_file.filename}' exceeds the 10 MB upload limit."
            )

        temp_output.write(output_content)
        output_temp_path = temp_output.name

    # --------------------------------------------------
    # 5. Extract output content
    # --------------------------------------------------

    try:
        extracted_output = process_file(output_temp_path)

    except Exception as error:
        return {
            "verdict": "invalid_output_file",
            "message": f"Could not process output file: {error}"
        }

    finally:
        Path(output_temp_path).unlink(missing_ok=True)

    # --------------------------------------------------
    # 6. Generate output hash
    # --------------------------------------------------

    output_hash = hash_content(extracted_output)

    # --------------------------------------------------
    # 7. Verify against MongoDB
    # --------------------------------------------------

    verification_result = verify_transformation(
        input_hash=input_hash,
        output_hash=output_hash
    )

    # Add hashes to response so frontend can display them.
    verification_result["input_hash"] = input_hash
    verification_result["output_hash"] = output_hash

    return verification_result