# 单元测试
# test_get_level.py
import pytest

from main import *


class TestPy01():

    def test001(self):
        result=(get_level(90), "优秀")

    def test002(self):
        result=(get_level(80), "良好")


if __name__ == '__main__':
    pytest.main()



