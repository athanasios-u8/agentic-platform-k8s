import argparse
import asyncio
from pathlib import Path

from bookstore_agents.common.config import get_settings
from bookstore_agents.vector_search.factory import create_vector_search_backend
from bookstore_agents.vector_search.reviews import (
    generate_review_documents,
    read_reviews_jsonl,
    write_reviews_jsonl,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure and populate the selected bookstore vector search backend."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    generate = subcommands.add_parser("generate-reviews", help="Generate local review JSONL.")
    generate.add_argument("--output", default=None, help="Output JSONL path.")

    subcommands.add_parser("create-index", help="Create or update the configured search index.")

    upload = subcommands.add_parser(
        "upload-reviews",
        help="Upload review JSONL to the configured search backend.",
    )
    upload.add_argument("--input", default=None, help="Input JSONL path.")

    rebuild = subcommands.add_parser(
        "rebuild",
        help="Generate reviews, create/update the index, and upload documents.",
    )
    rebuild.add_argument("--output", default=None, help="Output JSONL path.")

    return parser


async def _generate(path: str | None = None) -> Path:
    settings = get_settings()
    output_path = Path(path or settings.book_review_data_path)
    documents = await generate_review_documents()
    return write_reviews_jsonl(documents, output_path)


def main() -> None:
    args = build_parser().parse_args()
    settings = get_settings()

    if args.command == "generate-reviews":
        output_path = asyncio.run(_generate(args.output))
        documents = read_reviews_jsonl(output_path)
        print(f"Generated {len(documents)} review documents at {output_path}.")
        return

    if args.command == "create-index":
        backend = create_vector_search_backend(settings)
        backend.create_or_update_index()
        print(f"Created or updated {backend.provider_name} index {backend.index_name}.")
        return

    if args.command == "upload-reviews":
        input_path = Path(args.input or settings.book_review_data_path)
        documents = read_reviews_jsonl(input_path)
        backend = create_vector_search_backend(settings)
        uploaded = backend.upload_documents(documents)
        print(
            f"Uploaded {uploaded} review documents to "
            f"{backend.provider_name} index {backend.index_name}."
        )
        return

    if args.command == "rebuild":
        output_path = asyncio.run(_generate(args.output))
        backend = create_vector_search_backend(settings)
        backend.create_or_update_index()
        documents = read_reviews_jsonl(output_path)
        uploaded = backend.upload_documents(documents)
        print(
            f"Rebuilt {backend.provider_name} index {backend.index_name} with "
            f"{uploaded} review documents from {output_path}."
        )


if __name__ == "__main__":
    main()
