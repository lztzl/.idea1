from time import sleep
from selenium import webdriver

class TestailLogin:
  def setup(self):
      print("\nsetup")#创建浏览器驱动对象
      self.driver=webdriver.chrome()#浏览器最大化
      self.driver.maximize_window()# 打开指定网址
      self.driver.get("https://mail.163.com/")# 设置隐式等待
      self.driver.implicitly_wait(10)
  def test_mail_login(self):
      print("测试邮箱登录")# 定位iframe
      frame=self.driver.find_element_by_xpath("//*[@id=1oginDiv']/iframe")#切换frame
      self.driverswitch_toframe(frame)

      email_input=self.driver.find_element_by_name("email")# 输入的邮箱
      input_email="lztmsls@163.com"# 输入的密码

      input_password="Lzt05299"
      email_input.send_keys(input_email)
      sleep(1)# 定位密码
      password_input=self.driver.find_element_by_name("password")
      password_input.send_keys(input_password)
      sleep(1)
      login_button=self.driver.find_element_byid("dologin")
      login_button.click()
      sleep(2)
      # 定位账号文本
      email=self.driver.find_element_by_id("spnuid").text
      assert input_email in email
  def teardown(self):
      sleep(2)
      self.driver.quit()
      print("\nteardown")



