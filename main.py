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
from database import save_transformation
from hashing import hash_content, hash_file
from input_processor import process_file, process_text


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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Maps output_format -> correct Content-Type for the download,
# instead of always sending application/octet-stream.
MEDIA_TYPES = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "PNG": "image/png",
}

MAX_FILES = 5
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_SOURCE_TEXT_LENGTH = 100_000

@app.get("/")
def root():
    return {
        "message": "AI Content Transformation API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/transform")
async def transform_content(
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
    extracted_contents = []

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

    # Process text entered directly by the user
    if source_text.strip():
        extracted_contents.append(
            process_text(source_text)
        )

    # Process uploaded files
    for uploaded_file in files:

        file_extension = Path(uploaded_file.filename).suffix.lower()

        file_content = await uploaded_file.read()

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

            extracted_contents.append(
                f"===== {uploaded_file.filename} =====\n\n"
                f"{extracted_content}"
            )

        # Surfaces a clean error instead of a raw 500 if an image can't
        # be read (e.g. HF_TOKEN missing, or an unreadable image)
        except ValueError as error:
            return {
                "error": f"Could not process '{uploaded_file.filename}': {error}"
            }

        finally:
            Path(temp_file_path).unlink(missing_ok=True)

    # Make sure at least one source was provided
    if not extracted_contents:
        return {
            "error": "Please provide source text or upload at least one file."
        }

    # Combine all source content
    combined_source_content = "\n\n".join(extracted_contents)
    input_hash = hash_content(combined_source_content)
    transformation_prompt = build_transformation_prompt(
        source_content=combined_source_content,
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

    # Catches image-generation failures (e.g. missing HF_TOKEN)
    # cleanly instead of crashing with a raw 500
    try:
        generate_output(
            content=generated_content,
            output_format=output_format,
            output_path=str(output_file_path)
        )
        output_hash = hash_file(str(output_file_path))
        save_transformation(
        input_hash=input_hash,
        output_hash=output_hash
)

    except ValueError as error:
        return {
            "error": f"Could not generate {output_format} output: {error}"
        }

    background_tasks.add_task(output_file_path.unlink, missing_ok=True)

    return FileResponse(
        path=str(output_file_path),
        filename=f"transformed_content.{file_extension}",
        media_type=MEDIA_TYPES.get(output_format.upper(), "application/octet-stream"),
        background=background_tasks,
    )
