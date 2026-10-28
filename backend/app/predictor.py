from app.recommendation import recommend_jobs


class ResumePredictor:

    def __init__(self):
        print("Resume Predictor Initialized.")

    def predict(self, resume_text: str):

        recommendations = recommend_jobs(resume_text)

        return {
            "success": True,
            "recommendations": recommendations
        }


if __name__ == "__main__":

    predictor = ResumePredictor()

    resume = """
    Python
    Machine Learning
    TensorFlow
    SQL
    FastAPI
    Docker
    REST API
    """

    result = predictor.predict(resume)

    print(result)
