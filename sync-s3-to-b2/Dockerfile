FROM amazon/aws-lambda-python:3.9

WORKDIR /var/task

COPY sync_function.py requirements.txt ./

RUN pip install -r requirements.txt

CMD ["sync_function.handler"]
