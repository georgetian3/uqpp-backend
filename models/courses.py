import asyncio
from datetime import date, time, datetime, timedelta
from enum import Enum
from pprint import pprint
import re
from typing import List
from pydantic import BaseModel
from bs4 import BeautifulSoup, Tag
import aiohttp


CourseCategory = Enum('CourseType', 'FLEXIBLE_CORE RESEARCH UNDERGRADUATE_ELECTIVE POSTGRADUATE_ELECTIVE')
AttendenceMode = Enum('AttendenceMode', 'IN_PERSON EXTERNAL')
ActivityType = Enum('ActivityType', 'LECTURE PRACTICAL TUTORIAL STUDIO DELAYED')
AssessmentMethod = Enum('AssessmentMethod', 'ASSIGNMENT PROJECT EXAMINATION REPORT PRESENTATION')
Day = Enum('Day', 'MON TUE WED THU FRI SAT SUN')


    

class Activity(BaseModel):
    code: str
    location: str
    start_time: time
    end_time: time
    duration: int # minutes
    type: ActivityType
    day: Day
    dates: List[date]

class Offering(BaseModel):
    code: str
    semester: int
    campus: str
    attendence_mode: AttendenceMode
    faculty: str
    campus: str
    activities: List[Activity]


class Course(BaseModel):
    faculty: str
    school: str
    code: str
    name: str
    level: str
    units: int
    duration: str
    assessment_methods: str
    offerings: List[Offering]
    coordinator: str
    coordinator_email: str
    contact_hours: str





def add_time(t: time, d: timedelta) -> time:
    return (datetime(1, 1, 1, t.hour, t.minute) + d).time()

class CourseSelector:
    user_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    def __init__(self):
        ...

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *err):
        await self._session.close()
        self._session = None

    def _get_assessment_methods(self, summary: Tag) -> List[AssessmentMethod]:

        assessment_method_tag = summary.find(id='course-assessment-methods')
        assessment_methods = []
        for sibling in assessment_method_tag.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            assessment_methods.append(sibling.text.strip())
            if sibling.name != 'p':
                break
        return ', '.join(assessment_methods)

    async def get_course_info(self, course_code: str) -> Course:
        # main course page
        async with self._session.get(
            f'https://my.uq.edu.au/programs-courses/course.html?course_code={course_code}',
            headers=self.user_agent
        ) as response:
            html = await response.read()
        soup = BeautifulSoup(html, 'lxml')

        summary = soup.find(id='summary-content')
        if summary is None:
            return
        
        try:
            coordinator = re.match('(.+) ?\((.+)\)?', summary.find(id='course-coordinator').text)
            coordinator, email = [x.strip() for x in coordinator.groups()]
        except:
            coordinator, email = '', ''


        
        # timetable page
        async with self._session.post(
            f"https://timetable.my.uq.edu.au/{'odd' if datetime.now().year % 2 else 'even'}/rest/timetable/subjects",
            data=f'search-term={course_code}&semester=ALL&campus=ALL&faculty=ALL&type=ALL&days=1&days=2&days=3&days=4&days=5&days=6&days=0&start-time=00%3A00&end-time=23%3A00'
        ) as response:
            offerings_dict = await response.json()

        # print(json.dumps(offerings_dict))

        course = Course(
            code=course_code.upper(),
            name=re.match('(.+) \(.{8}\)', soup.find(id='course-title').text).group(1),
            level=summary.find(id='course-level').text,
            faculty=summary.find(id='course-faculty').text.strip(),
            school=summary.find(id='course-school').text.strip(),
            units=int(summary.find(id='course-units').text),
            duration=summary.find(id='course-duration').text,
            assessment_methods=self._get_assessment_methods(summary),
            coordinator=coordinator,
            coordinator_email=email,
            contact_hours=summary.find(id='course-contact').text,
            offerings=[],
        )

        if not offerings_dict:
            return course

        offerings: List[Offering] = []

        for offering in offerings_dict.values():
            _, semester, campus, attendence_mode = offering['subject_code'].split('_')
            semester = int(semester[1])
            if attendence_mode == 'IN':
                attendence_mode = AttendenceMode.IN_PERSON
            elif attendence_mode == 'EX':
                attendence_mode = AttendenceMode.EXTERNAL
            else:
                raise Exception(f'Invalid attendence mode for course {course_code}: {attendence_mode}')
            
            activities: List[Activity] = []
            for activity_dict in offering['activities'].values():
                print(activity_dict['activity_group_code'], activity_dict['activity_code'], activity_dict['activity_type'])
                activity_start_time = datetime.strptime(activity_dict['start_time'], '%H:%M').time()
                activity_duration = int(activity_dict['duration'])
                activity_end_time = add_time(activity_start_time, timedelta(minutes=activity_duration))

                activities.append(Activity(
                    code=activity_dict['activity_code'],
                    location=activity_dict['location'],
                    dates=[datetime.strptime(activity_date, '%d/%m/%Y').date() for activity_date in activity_dict['activitiesDays']],
                    type=ActivityType[activity_dict['activity_type'].upper()],
                    day=Day[activity_dict['day_of_week'].upper()],
                    start_time=activity_start_time,
                    end_time=activity_end_time,
                    duration=activity_duration,
                ))
            offering = Offering(
                code=offering['subject_code'],
                semester=semester,
                campus=campus,
                attendence_mode=attendence_mode,
                faculty=offering['faculty'],
                activities=activities
            )
            offerings.append(offering)
        
        print('offerings', offerings)
        course.offerings = offerings
        
        return course
    
    # def get_courses(self) -> List[Course]:
    #     try:
    #         with open('uq-mcs.html') as f:
    #             html = f.read()
    #     except FileNotFoundError:
    #         html = requests.get(
    #             'https://my.uq.edu.au/programs-courses/requirements/program/5522/2024',
    #             headers=self.user_agent
    #         ).text

    #         with open('uq-mcs.html', 'w') as f:
    #             f.write(html)


    #     soup = BeautifulSoup(html, 'lxml')

    #     courses: List[Course] = []


    #     for course_type in CourseCategory:
    #         course_category_div = soup.find(id=f'part-A.{course_type.value}')
    #         if isinstance(course_category_div, Tag):
    #             courses_raw = course_category_div.find_all('a')
    #         else:
    #             raise Exception(f'Cannot find course category: part-A.{course_type.value}')
    #         for course_raw in courses_raw:
    #             course_code = course_raw.find(class_='curriculum-reference__code').text
    #             course_level = int(course_code[4])
    #             course = Course(
    #                 category=course_type,
    #                 code=course_code,
    #                 name=course_raw.find(class_='curriculum-reference__name').text,
    #                 units=int(course_raw.find(class_='curriculum-reference__units').text.split()[0]),
    #                 level=course_level
    #             )
    #             courses.append(course)

    #     return courses

    def satisfies_requirements(self, courses: List[Course]) -> bool:
        requirements_satisfied = True
        if sum([course.units for course in courses]) < 24:
            requirements_satisfied = False
            print('Complete 24 units')
        if sum([course.units for course in courses if course.level >= 6]) < 12:
            requirements_satisfied = False
            print('Selected courses must include at least 12 units at level 6 or higher.')
        if sum([course.units for course in courses if course.level >= 7]) < 8:
            requirements_satisfied = False
            print('Selected courses must include at least 8 units at level 7.')
        if not 6 <= sum([course.units for course in courses if course.category == CourseCategory.FLEXIBLE_CORE]) <= 20:
            requirements_satisfied = False
            print('6 to 20 units from MCompSc Flexible Core Courses')
        if not 4 <= sum([course.units for course in courses if course.category == CourseCategory.RESEARCH]) <= 10:
            requirements_satisfied = False
            print('4 to 10 units from MCompSc Research Courses')
        if not 0 <= sum([course.units for course in courses if course.category == CourseCategory.UNDERGRADUATE_ELECTIVE]) <= 6:
            requirements_satisfied = False
            print('0 to 6 units from MCompSc Advanced Undergraduate Elective Courses')
        if not 0 <= sum([course.units for course in courses if course.category == CourseCategory.POSTGRADUATE_ELECTIVE]) <= 8:
            requirements_satisfied = False
            print('0 to 8 units from MCompSc Postgraduate Elective Courses')
        return requirements_satisfied

async def main():
    async with CourseSelector() as s:
        course = await s.get_course_info('CSSE6400')
    pprint(course.model_dump())
    return
    courses = s.get_courses()

    selected_course_codes = (
        'CSSE6400', # Software Architecture
        'COMP7110', # Introduction to Software Innovation
        'CSSE7610', # Concurrency: Theory and Practice
        'COMP7500', # Advanced Algorithms and Data Structures
        'COMP7812', # Computer Science Research Project, commencing semester 2
        'INFS3208', # Cloud Computing
        'INFS7202', # Web Information Systems
    )


    selected_courses = [course for course in courses if course.code in selected_course_codes]

    s.satisfies_requirements(selected_courses)
if __name__ == '__main__':
    asyncio.run(main())