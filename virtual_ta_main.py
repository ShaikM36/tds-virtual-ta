from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import os
import openai
import base64
import io
from PIL import Image
import json
import re
from datetime import datetime

app = FastAPI(title="TDS Virtual TA", description="Virtual Teaching Assistant for TDS Course")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QuestionRequest(BaseModel):
    question: str
    image: Optional[str] = None

class LinkResponse(BaseModel):
    url: str
    text: str

class AnswerResponse(BaseModel):
    answer: str
    links: List[LinkResponse]

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sample TDS knowledge base (you should expand this with real scraped data)
TDS_KNOWLEDGE_BASE = {
    "course_content": [
        {
            "topic": "AI Models and APIs",
            "content": "For TDS assignments, you must use gpt-3.5-turbo-0125 model specifically, even if AI Proxy supports other models like gpt-4o-mini. Use OpenAI API directly when required.",
            "source": "Course Guidelines"
        },
        {
            "topic": "Data Collection",
            "content": "Web scraping should be done ethically with proper rate limiting. Use libraries like requests, BeautifulSoup, and selenium when needed.",
            "source": "Week 3 Materials"
        },
        {
            "topic": "API Development",
            "content": "FastAPI is recommended for building REST APIs. Ensure proper error handling and response formatting.",
            "source": "Week 5 Materials"
        }
    ],
    "discourse_posts": [
        {
            "url": "https://discourse.onlinedegree.iitm.ac.in/t/ga5-question-8-clarification/155939/4",
            "title": "GA5 Question 8 Clarification",
            "content": "Use the model that's mentioned in the question. For token counting, use the specified model's tokenizer.",
            "date": "2025-04-10"
        },
        {
            "url": "https://discourse.onlinedegree.iitm.ac.in/t/api-best-practices/155940/2",
            "title": "API Best Practices",
            "content": "Always implement proper error handling and return appropriate HTTP status codes.",
            "date": "2025-04-08"
        }
    ]
}

def process_image(base64_image: str) -> str:
    """Process base64 image and return description"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(base64_image)
        image = Image.open(io.BytesIO(image_data))
        
        # For now, return basic image info
        # In a real implementation, you'd use OCR or image analysis
        return f"Image processed: {image.format} format, size: {image.size}"
    except Exception as e:
        return f"Error processing image: {str(e)}"

def search_knowledge_base(question: str) -> List[dict]:
    """Search knowledge base for relevant information"""
    question_lower = question.lower()
    relevant_items = []
    
    # Search course content
    for item in TDS_KNOWLEDGE_BASE["course_content"]:
        if any(keyword in question_lower for keyword in ["api", "model", "gpt", "openai", "scraping", "fastapi"]):
            if any(keyword in item["content"].lower() for keyword in ["api", "model", "gpt", "openai", "scraping", "fastapi"]):
                relevant_items.append(item)
    
    # Search discourse posts
    for post in TDS_KNOWLEDGE_BASE["discourse_posts"]:
        if any(keyword in question_lower for keyword in ["question", "clarification", "api", "model"]):
            if any(keyword in post["content"].lower() for keyword in ["model", "api", "token", "question"]):
                relevant_items.append(post)
    
    return relevant_items

def generate_answer(question: str, relevant_items: List[dict], image_description: str = None) -> str:
    """Generate answer using OpenAI API"""
    try:
        context = "\n".join([item.get("content", "") for item in relevant_items])
        
        prompt = f"""You are a Teaching Assistant for the Tools in Data Science (TDS) course at IIT Madras.
        
Question: {question}

Context from course materials and discourse:
{context}

{f"Image description: {image_description}" if image_description else ""}

Provide a helpful, accurate answer based on the TDS course content. Be specific and practical."""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a helpful TDS course Teaching Assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback answer if OpenAI API fails
        if relevant_items:
            return f"Based on course materials: {relevant_items[0].get('content', 'Please refer to course materials for detailed information.')}"
        return "I apologize, but I'm having trouble accessing the course information right now. Please check the course materials or post your question on Discourse."

def get_relevant_links(relevant_items: List[dict]) -> List[LinkResponse]:
    """Extract relevant links from search results"""
    links = []
    
    for item in relevant_items:
        if "url" in item:
            links.append(LinkResponse(
                url=item["url"],
                text=item.get("title", item.get("content", "")[:100])
            ))
    
    # Add some default helpful links if no specific ones found
    if not links:
        links.append(LinkResponse(
            url="https://discourse.onlinedegree.iitm.ac.in/c/degree-programs/tools-in-data-science/123",
            text="TDS Course Discourse Forum"
        ))
    
    return links[:3]  # Limit to 3 links

@app.get("/")
async def root():
    return {"message": "TDS Virtual TA API is running", "timestamp": datetime.now().isoformat()}

@app.post("/api/", response_model=AnswerResponse)
async def answer_question(request: QuestionRequest):
    """Main API endpoint to answer student questions"""
    try:
        # Process image if provided
        image_description = None
        if request.image:
            image_description = process_image(request.image)
        
        # Search knowledge base
        relevant_items = search_knowledge_base(request.question)
        
        # Generate answer
        answer = generate_answer(request.question, relevant_items, image_description)
        
        # Get relevant links
        links = get_relevant_links(relevant_items)
        
        return AnswerResponse(
            answer=answer,
            links=links
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)