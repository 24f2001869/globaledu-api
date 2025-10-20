import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import uvicorn

# Initialize the FastAPI application
app = FastAPI(
    title="Wikipedia Country Outline API",
    description="An API to fetch the hierarchical outline of a country's Wikipedia page as Markdown.",
    version="1.0.1", # Version updated
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- API Endpoint ---
@app.get(
    "/api/outline",
    summary="Get Wikipedia Outline for a Country",
    response_class=Response,
    responses={
        200: {
            "description": "Successfully retrieved the Markdown outline.",
            "content": {"text/plain": {"example": "## Contents\n# United States\n## Etymology\n## History\n### Colonial period"}},
        },
        404: {"description": "Country not found on Wikipedia."},
        500: {"description": "Internal server error or failed to fetch data."},
    },
)
async def get_country_outline(country: str):
    """
    Fetches the Wikipedia page for a given country, extracts all headings
    (H1 through H6), and returns them as a structured Markdown outline.

    - **country**: The name of the country to look up (e.g., "United States", "India").
    """
    formatted_country = country.replace(" ", "_")
    wikipedia_url = f"https://en.wikipedia.org/wiki/{formatted_country}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(wikipedia_url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml') # Using lxml for performance

        # To get the title, we find the first H1 tag, which is the page title.
        title_heading = soup.find('h1', id='firstHeading')
        
        # Then we get the rest of the headings from the main content div.
        content_div = soup.find(id="mw-content-text")

        if not content_div:
            raise HTTPException(status_code=500, detail="Could not find the main content area of the Wikipedia page.")

        headings = content_div.find_all(['h2', 'h3', 'h4', 'h5', 'h6']) # Start from H2 in content

        markdown_outline = []
        
        # Add the main page title (H1) first if it exists
        if title_heading:
            markdown_outline.append(f"# {title_heading.get_text(strip=True)}")

        # --- Generate Markdown Outline ---
        for heading in headings:
            text = heading.get_text(strip=True).replace('[edit]', '').replace('[Edit]', '')
            
            # This is the corrected logic. We NO LONGER skip "Contents".
            
            level = int(heading.name[1])
            markdown_outline.append(f"{'#' * level} {text}")

        final_outline = "\n".join(markdown_outline)

        return Response(content=final_outline, media_type="text/plain; charset=utf-8")

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Wikipedia page for '{country}' not found.")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch data from Wikipedia: {exc}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# uvicorn main:app --reload

