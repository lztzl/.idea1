# 单元测试
# test_get_level.py
import pytest

from main import *


class TestPy01():

    def testPy001(self):
        self.assertEquals(get_level(90), "优秀")

    def testPy002(self):
        self.assertEquals(get_level(80), "良好")


if __name__ == '__main__':
    pytest.main()



