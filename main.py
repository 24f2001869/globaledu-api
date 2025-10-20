import httpx
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from bs4 import BeautifulSoup
import uvicorn

# Initialize the FastAPI application
app = FastAPI(
    title="Wikipedia Country Outline API",
    description="An API to fetch the hierarchical outline of a country's Wikipedia page as Markdown.",
    version="1.0.0",
)

# --- CORS Configuration ---
# This middleware allows the API to be accessed from any web domain.
# This is crucial for GlobalEdu's various educational platforms to be able
# to fetch data from this API without running into browser security issues.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["GET"],  # Allow only GET requests
    allow_headers=["*"],   # Allow all headers
)

# --- API Endpoint ---
@app.get(
    "/api/outline",
    summary="Get Wikipedia Outline for a Country",
    response_class=Response,
    responses={
        200: {
            "description": "Successfully retrieved the Markdown outline.",
            "content": {"text/plain": {"example": "# United States\n## Etymology\n## History\n### Colonial period"}},
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
    # Format the country name for the Wikipedia URL (e.g., "United States" -> "United_States")
    formatted_country = country.replace(" ", "_")
    wikipedia_url = f"https://en.wikipedia.org/wiki/{formatted_country}"

    try:
        # Use an async HTTP client to fetch the page content
        async with httpx.AsyncClient() as client:
            response = await client.get(wikipedia_url)
            # Raise an exception for bad status codes (like 404 Not Found)
            response.raise_for_status()

        # Parse the HTML content of the page using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main content area to avoid including sidebars or footers
        content_div = soup.find(id="mw-content-text")
        if not content_div:
            raise HTTPException(status_code=500, detail="Could not find the main content area of the Wikipedia page.")

        # Find all heading tags within the main content
        headings = content_div.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        # --- Generate Markdown Outline ---
        markdown_outline = []
        for heading in headings:
            # Get the heading text, cleaning out any nested tags like [edit] links
            text = heading.get_text(strip=True).replace('[edit]', '').replace('[Edit]', '')
            
            # Skip the main "Contents" heading as it's redundant
            if "Contents" in text:
                continue
            
            # Determine the level of the heading (h1 -> #, h2 -> ##, etc.)
            level = int(heading.name[1])
            markdown_outline.append(f"{'#' * level} {text}")

        # Join all markdown lines into a single string
        final_outline = "\n".join(markdown_outline)

        # Return the final string as a plain text response
        return Response(content=final_outline, media_type="text/plain")

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Wikipedia page for '{country}' not found.")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to fetch data from Wikipedia: {exc}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# To run this application locally, save the code as main.py and run the following command in your terminal:
# uvicorn main:app --reload
#
# Then, you can access the API at http://127.0.0.1:8000/api/outline?country=YourCountryName
