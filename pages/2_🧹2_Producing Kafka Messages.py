import streamlit as st
from utils import st_def
import datetime
import functools
import logging
from typing import Callable, Dict, List

from newsapi import NewsApiClient
from newsdataapi import NewsDataApiClient
from pydantic import ValidationError

from utils.models import NewsAPIModel, NewsDataIOModel
from utils.settings import settings

st_def.st_logo(title = "Welcome 👋 to Text Cleaning!", page_title="Text Cleaning",)
st_def.st_read_pdf()
#------------------------------------------------------------------------
def run(self) -> NoReturn:
        """Continuously fetch and send messages to a Kafka topic."""
        while self.running.is_set():
            try:
                messages: List[CommonDocument] = self.fetch_function()
                if messages:
                    messages = [msg.to_kafka_payload() for msg in messages]
                    self.producer.send(self.topic, value=messages)
                    self.producer.flush()
                logger.info(
                    f"Producer : {self.producer_id} sent: {len(messages)} msgs."
                )
                time.sleep(self.wait_window_sec)
            except Exception as e:
                logger.error(f"Error in producer worker {self.producer_id}: {e}")
                self.running.clear()  # Stop the thread on error
                
                
class CommonDocument(BaseModel):
    article_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(default_factory=lambda: "N/A")
    url: str = Field(default_factory=lambda: "N/A")
    published_at: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    source_name: str = Field(default_factory=lambda: "Unknown")
    image_url: Optional[str] = Field(default_factory=lambda: None)
    author: Optional[str] = Field(default_factory=lambda: "Unknown")
    description: Optional[str] = Field(default_factory=lambda: None)
    content: Optional[str] = Field(default_factory=lambda: None)

    @field_validator("title", "description", "content")
    def clean_text_fields(cls, v):
        if v is None or v == "":
            return "N/A"
        return clean_full(v)

    @field_validator("url", "image_url")
    def clean_url_fields(cls, v):
        if v is None:
            return "N/A"
        v = remove_html_tags(v)
        v = normalize_whitespace(v)
        return v

    @field_validator("published_at")
    def clean_date_field(cls, v):
        try:
            parsed_date = parser.parse(v)
            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            logger.error(f"Error parsing date: {v}, using current date instead.")

    @classmethod
    def from_json(cls, data: dict) -> "CommonDocument":
        """Create a CommonDocument from a JSON object."""
        return cls(**data)

    def to_kafka_payload(self) -> dict:
        """Prepare the common representation for Kafka payload."""
        return self.model_dump(exclude_none=False)