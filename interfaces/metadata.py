from typing import Any
from pydantic import BaseModel


class Metadata(BaseModel):
    """
    Metadata for the dataset.

    Attributes:
        law_type (str): The type of law (e.g., "Civil", "Criminal").
        article_number (int): The article number.
        article_title_number (int): The article title number.
        file_path (str): The path to the file.
    """
    
    law_type: str
    article_number: str
#    article_title_number: str | int 
    file_path: str

    @classmethod
    def model_safe_validate(cls, data: dict[str, str | int]):
        """
        Validate the metadata model.

        Args:
            data (dict): The data to validate.

        Returns:
            bool: True if the data is valid, False otherwise.
        """
        data["article_number"] = str(data["article_number"])
        return cls.model_validate(data)