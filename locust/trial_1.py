from locust import HttpLocust, TaskSet, task

def projects_query(l):
    response = l.client.request(method="GET", url="/projects",
                   auth=('admin','contrail123'))

class UserTasks(TaskSet):
    # one can specify tasks like this
    tasks = [projects_query]

class WebsiteUser(HttpLocust):
    """
    Locust user class that does requests to the locust web server running on localhost
    """
    host = "http://127.0.0.1:8095"
    min_wait = 100
    max_wait = 100
    task_set = UserTasks
