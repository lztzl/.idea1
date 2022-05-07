FROM python
WORKDIR .
ADD . .
RUN pip install -r requirements.txt
CMD ["pytest", "-q","TestCase/AIMP/Connect/AIMP_Connect_01.py","--alluredir","allure-results"]