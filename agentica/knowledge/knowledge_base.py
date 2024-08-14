# -*- coding: utf-8 -*-
"""
@author:XuMing(xuming624@qq.com)
@description: 
part of the code from https://github.com/phidatahq/phidata
"""
import re
from pathlib import Path
from typing import List, Optional, Iterator, Dict, Any, Union

from pydantic import BaseModel, ConfigDict

from agentica.document import Document
from agentica.tools.url_crawler import UrlCrawlerTool
from agentica.utils.file_parser import (
    read_json_file,
    read_csv_file,
    read_txt_file,
    read_pdf_file,
    read_pdf_url,
    read_docx_file,
    read_excel_file
)
from agentica.utils.log import logger
from agentica.vectordb.base import VectorDb


class KnowledgeBase(BaseModel):
    """LLM knowledge base, which is a collection of documents."""

    # Input knowledge base file path, which can be a file or a directory or a URL
    data_path: Union[str, List[str]] = []
    # Embeddings db to store the knowledge base
    vector_db: Optional[VectorDb] = None
    # Number of relevant documents to return on search
    num_documents: int = 2
    # Number of documents to optimize the vector db on
    optimize_on: Optional[int] = 2000

    chunk_size: int = 4000
    chunk: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean the text by replacing multiple newlines with a single newline"""

        # Replace multiple newlines with a single newline
        cleaned_text = re.sub(r"\n+", "\n", text)
        # Replace multiple spaces with a single space
        cleaned_text = re.sub(r"\s+", " ", cleaned_text)
        # Replace multiple tabs with a single tab
        cleaned_text = re.sub(r"\t+", "\t", cleaned_text)
        # Replace multiple carriage returns with a single carriage return
        cleaned_text = re.sub(r"\r+", "\r", cleaned_text)
        # Replace multiple form feeds with a single form feed
        cleaned_text = re.sub(r"\f+", "\f", cleaned_text)
        # Replace multiple vertical tabs with a single vertical tab
        cleaned_text = re.sub(r"\v+", "\v", cleaned_text)

        return cleaned_text

    def chunk_document(self, document: Document, chunk_size: int = 4000) -> List[Document]:
        """Chunk the document content into smaller documents"""
        content = document.content
        cleaned_content = self._clean_text(content)
        content_length = len(cleaned_content)
        chunked_documents: List[Document] = []
        chunk_number = 1
        chunk_meta_data = document.meta_data

        start = 0
        while start < content_length:
            end = start + chunk_size

            # Ensure we're not splitting a word in half
            if end < content_length:
                while end > start and cleaned_content[end] not in [" ", "\n", "\r", "\t"]:
                    end -= 1

            # If the entire chunk is a word, then just split it at self.chunk_size
            if end == start:
                end = start + chunk_size

            # If the end is greater than the content length, then set it to the content length
            if end > content_length:
                end = content_length

            chunk = cleaned_content[start:end]
            meta_data = chunk_meta_data.copy()
            meta_data["chunk"] = chunk_number
            chunk_id = None
            if document.id:
                chunk_id = f"{document.id}_{chunk_number}"
            elif document.name:
                chunk_id = f"{document.name}_{chunk_number}"
            meta_data["chunk_size"] = len(chunk)
            chunked_documents.append(
                Document(
                    id=chunk_id,
                    name=document.name,
                    meta_data=meta_data,
                    content=chunk,
                )
            )
            chunk_number += 1
            start = end
        return chunked_documents

    def read_file(self, path: Union[Path, str]) -> List[Document]:
        """
        Reads a file and returns a list of documents.
        """
        path = Path(path) if isinstance(path, str) else path
        if not path:
            raise ValueError("No path provided")

        if not path.exists():
            raise FileNotFoundError(f"Could not find file: {path}")

        try:
            file_name = path.name.split("/")[-1].split(".")[0].replace("/", "_").replace(" ", "_")
            if path.suffix in [".json", ".jsonl"]:
                file_contents = read_json_file(path)
            elif path.suffix in [".csv"]:
                file_contents = read_csv_file(path)
            elif path.suffix in [".txt"]:
                file_contents = read_txt_file(path)
            elif path.suffix in [".pdf"]:
                file_contents = read_pdf_file(path)
            elif path.suffix in [".doc", ".docx"]:
                if path.suffix == ".doc":
                    raise ValueError("Unsupported doc format. Please convert to docx.")
                file_contents = read_docx_file(path)
            elif path.suffix in [".xls", ".xlsx"]:
                file_contents = read_excel_file(path)
            else:
                raise ValueError(f"Unsupported file format: {path.suffix}")
            documents = [
                Document(
                    name=file_name,
                    id=file_name,
                    content=file_contents,
                )
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document, self.chunk_size))
                return chunked_documents
            return documents
        except Exception as e:
            logger.error(f"Error reading: {path}: {e}")
        return []

    def read_pdf_url(self, path: str) -> List[Document]:
        """
        Reads a pdf from a URL and returns a list of documents.
        """
        try:
            file_contents = read_pdf_url(path)
            documents = [
                Document(
                    name=path,
                    id=path,
                    content=file_contents,
                )
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document, self.chunk_size))
                return chunked_documents
            return documents
        except Exception as e:
            logger.error(f"Error reading: {path}: {e}")
        return []

    def read_url(self, url: str) -> List[Document]:
        """
        Reads a website and returns a list of documents.
        """
        try:
            content = UrlCrawlerTool().url_crawl(url)
            documents = [
                Document(
                    name=url,
                    id=url,
                    content=content,
                )
            ]
            if self.chunk:
                chunked_documents = []
                for document in documents:
                    chunked_documents.extend(self.chunk_document(document, self.chunk_size))
                return chunked_documents
            return documents
        except Exception as e:
            logger.error(f"Error reading: {url}: {e}")
        return []

    @property
    def document_lists(self) -> Iterator[List[Document]]:
        """Iterator that yields lists of documents in the knowledge base
        Each object yielded by the iterator is a list of documents.
        """
        if isinstance(self.data_path, str):
            self.data_path = [self.data_path]
        for path in self.data_path:
            _file_path: Path = Path(path)
            if _file_path.exists() and _file_path.is_dir():
                for _file in _file_path.glob("**/*"):
                    if _file_path.suffix:
                        yield self.read_file(_file)
            elif _file_path.exists() and _file_path.is_file() and _file_path.suffix:
                yield self.read_file(_file_path)
            elif path.startswith("http") and 'pdf' in path:
                yield self.read_pdf_url(path)
            elif path.startswith("http"):
                yield self.read_url(path)
            else:
                raise ValueError(f"Unsupported file format: {path}")

    def search(self, query: str, num_documents: Optional[int] = None) -> List[Document]:
        """Returns relevant documents matching the query"""
        try:
            if self.vector_db is None:
                logger.warning("No vector db provided")
                return []

            _num_documents = num_documents or self.num_documents
            logger.debug(f"Getting {_num_documents} relevant documents for query: {query}")
            return self.vector_db.search(query=query, limit=_num_documents)
        except Exception as e:
            logger.error(f"Error searching for documents: {e}")
            return []

    def load(self, recreate: bool = False, upsert: bool = False, skip_existing: bool = True) -> None:
        """Load the knowledge base to the vector db

        Args:
            recreate (bool): If True, recreates the collection in the vector db. Defaults to False.
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db when inserting.
                Defaults to True.
        """

        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        if recreate:
            logger.info("Deleting collection")
            self.vector_db.delete()

            logger.info("Creating collection")
            self.vector_db.create()

        logger.info("Loading knowledge base")
        num_documents = 0
        for document_list in self.document_lists:
            documents_to_load = document_list
            # Upsert documents if upsert is True and vector db supports upsert
            if upsert and self.vector_db.upsert_available():
                self.vector_db.upsert(documents=documents_to_load)
            # Insert documents
            else:
                # Filter out documents which already exist in the vector db
                if skip_existing:
                    documents_to_load = [
                        document for document in document_list if not self.vector_db.doc_exists(document)
                    ]
                self.vector_db.insert(documents=documents_to_load)
            num_documents += len(documents_to_load)
            logger.info(f"Added {len(documents_to_load)} documents to knowledge base")

        if self.optimize_on is not None and num_documents > self.optimize_on:
            logger.info("Optimizing Vector DB")
            self.vector_db.optimize()

    def load_documents(self, documents: List[Document], upsert: bool = False, skip_existing: bool = True) -> None:
        """Load documents to the knowledge base

        Args:
            documents (List[Document]): List of documents to load
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db when inserting.
                Defaults to True.
        """

        logger.info("Loading knowledge base")
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return

        # Upsert documents if upsert is True
        if upsert and self.vector_db.upsert_available():
            self.vector_db.upsert(documents=documents)
            logger.info(f"Loaded {len(documents)} documents to knowledge base")
            return

        # Filter out documents which already exist in the vector db
        documents_to_load = (
            [document for document in documents if not self.vector_db.doc_exists(document)]
            if skip_existing
            else documents
        )

        # Insert documents
        if len(documents_to_load) > 0:
            self.vector_db.insert(documents=documents_to_load)
            logger.info(f"Loaded {len(documents_to_load)} documents to knowledge base")
        else:
            logger.info("No new documents to load")

    def load_document(self, document: Document, upsert: bool = False, skip_existing: bool = True) -> None:
        """Load a document to the knowledge base

        Args:
            document (Document): Document to load
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db. Defaults to True.
        """
        self.load_documents(documents=[document], upsert=upsert, skip_existing=skip_existing)

    def load_dict(self, document: Dict[str, Any], upsert: bool = False, skip_existing: bool = True) -> None:
        """Load a dictionary representation of a document to the knowledge base

        Args:
            document (Dict[str, Any]): Dictionary representation of a document
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db. Defaults to True.
        """
        self.load_documents(documents=[Document.from_dict(document)], upsert=upsert, skip_existing=skip_existing)

    def load_json(self, document: str, upsert: bool = False, skip_existing: bool = True) -> None:
        """Load a json representation of a document to the knowledge base

        Args:
            document (str): Json representation of a document
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db. Defaults to True.
        """
        self.load_documents(documents=[Document.from_json(document)], upsert=upsert, skip_existing=skip_existing)

    def load_text(self, text: str, upsert: bool = False, skip_existing: bool = True) -> None:
        """Load a text to the knowledge base

        Args:
            text (str): Text to load to the knowledge base
            upsert (bool): If True, upserts documents to the vector db. Defaults to False.
            skip_existing (bool): If True, skips documents which already exist in the vector db. Defaults to True.
        """
        self.load_documents(documents=[Document(content=text)], upsert=upsert, skip_existing=skip_existing)

    def exists(self) -> bool:
        """Returns True if the knowledge base exists"""
        if self.vector_db is None:
            logger.warning("No vector db provided")
            return False
        return self.vector_db.exists()

    def clear(self) -> bool:
        """Clear the knowledge base"""
        if self.vector_db is None:
            logger.warning("No vector db available")
            return True

        return self.vector_db.clear()
