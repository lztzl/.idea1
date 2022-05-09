import allure
import pytest
import time


@allure.epic('Web测试')
@allure.severity('blocker')
@allure.feature('用户登录模块')
class TestLogin:


    def setup(self):
        pass

    def teardown(self):
        time.sleep(3)

    @allure.story('用户登陆')
    @allure.title('测试数据')
    def test01_login(self):
        print("test")


