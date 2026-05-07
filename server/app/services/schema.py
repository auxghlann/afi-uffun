from pydantic import BaseModel, Field
from typing import Literal, List

class EmergencyDetails(BaseModel):
    """
    Structured information extracted by the First Responder AI once it has gathered enough details from the caller.
    """
    emergency_types: str = Field(description="Comma-separated list of relevant responder types needed for this emergency. Choose from: Fire, Medical, Police, Rescue. Example: 'Police, Medical' for an accident with injuries, or 'Fire, Rescue' for a building fire with trapped people.")
    severity: Literal["High", "Medium", "Low"] = Field(description="The severity level of the emergency based on urgency and threat to life or property.")
    people_affected: str = Field(description="The estimated number of people affected by the emergency as a string (e.g. '0', '1', 'many').", default="0")
    is_ongoing: str = Field(description="Return 'True' if the emergency is currently happening, 'False' if it has already passed.")
    location_details: str = Field(description="Any specific details about the location gathered from the caller (e.g., specific landmarks, floor number).")
    summary: str = Field(description="A clean, objective 1-2 sentence summary of the emergency situation.")
