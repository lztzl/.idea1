# 单元测试
# test_get_level.py
import pytest

from main import *


#class TestPy01():


  #  def test001(self):
    #    result=(get_level(90), "优秀")

  #  def test002(self):
       # result=(get_level(80), "良好")


#if __name__ == '__main__':
   # pytest.main(["--cov=./testcases/""--cov-report=html"])


from main import loginAndCheck


class Test_哔哩登陆:
    def test_UI_001(self):
      print('\n用例 UI_001')
      alertTex=loginAndCheck(None,'5465468')
      assert alertTex=={"请输入注册时用的邮箱或者手机号呀:"}

    def test_UI_002(self):
        print('\n用例 UI_002')

        alertTex=loginAndCheck('KKC12345',None)
        assert alertTex =={'':"喵，你没输入密码么?"}

	def test_UI_003(self):\
        print('\n用例 UI_003')
        alertTex=loginAndCheck(None,None)
        assert alertTex=={"请输入注册时用的邮箱或者手机号呀":"喵，你没输入密码么?"}

