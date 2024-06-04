import json
from fastapi import FastAPI

from models.courses import Course, CourseSelector

class Api(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(
            title='UQPP API',
            version='1.0.0',
            root_path='/api/v1',
        )
        
        @self.get('/course/{course_code}', response_model=Course)
        async def get_course_info(course_code: str):
            s = CourseSelector()
            return await s.get_course_info(course_code)
        
    def get_openapi(self):
        with open('openapi.json', 'w') as f:
            json.dump(self.openapi(), f, indent=2)