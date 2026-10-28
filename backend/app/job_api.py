import os
import requests
from dotenv import load_dotenv

# Load environment variables
# load_dotenv()
from pathlib import Path

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

API_KEY = os.getenv("RAPIDAPI_KEY")
# print("API KEY:", API_KEY)

URL = "https://jsearch.p.rapidapi.com/search-v2"


def search_jobs(job_role):

    querystring = {
        "query": f"{job_role} jobs",
        "num_pages": "1",
        "country": "us",
        "date_posted": "all"
    }

    headers = {
        "x-rapidapi-key": API_KEY,
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.get(
        URL,
        headers=headers,
        params=querystring
    )

    data = response.json()

    jobs = []

    # If API returns an error
    if "data" not in data:
        print("API Error:", data)
        return jobs

    job_list = data["data"].get("jobs", [])

    for job in job_list:

        jobs.append({

            "company": job.get("employer_name"),

            "job_title": job.get("job_title"),

            "location": job.get("job_location"),

            "employment_type": job.get("job_employment_type"),

            "salary": job.get("job_salary_string"),

            "posted_date": job.get("job_posted_at"),

            "apply_link": job.get("job_apply_link")

        })

    return jobs


if __name__ == "__main__":

    jobs = search_jobs("Backend Developer")

    print(jobs)