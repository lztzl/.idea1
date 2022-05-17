# 切记，py文件也要以“test_”开头
import pytest  # 首先引入pytest。简单的例子不引入也能运行


def add(x):  # 先申明1个函数“返回传值+2”，做为测试使用
    return x + 2


class Test_Class_Add():  # 先定义1个类，一定要以“test_”开头
    def test_add1(self):  # 定义测试用户，一定要以“test_”开头
        assert add(2) == 5  # 使用assert进行断言，是否相等

    def test_add2(self):
        assert add(22) == 24

    def test_add3(self):
        assert add(100) == 102


class Test_Class_In():  # 定义第2个类
    def test_in(self):
        a = "Hello World！"
        b = "Hi"
        c = "World"
        assert c in a  # 使用in和not in进行断言
        assert b not in a

    def test_notin(self):
        assert b in a
        assert c not in a

