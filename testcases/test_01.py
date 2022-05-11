# 单元测试
# test_get_level.py
import pytest

from main import *


class GetLevel(pytest.TestCase):

    def test_get_level1(self):
        self.assertEquals(get_level(90), "优秀")

    def test_get_level2(self):
        self.assertEquals(get_level(80), "良好")


if __name__ == '__main__':
    pytest.main(verbosity=2)



