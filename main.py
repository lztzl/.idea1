# 被测代码
# main.py
  #def get_level(cource):
   # """
   # 自定义的方法
  #  :param cource:成绩
   # :return:
   # """
    #if cource >= 90:
   #     return "优秀"
  #  elif cource >= 80:
   #     return "良好"
    #elif cource >= 60:
     #   return "合格"
    #elif cource >= 40:
       # return "不合格"
   # else:
      #  return "差"


from selenium import webdriver
from time import sleep
def loginAndCheck(username=None,passwd=None):
    driver = webdriver.Chrome(r'd:\Chromedriver.exe')
    driver.implicitly_wait(5)

    driver.get('https://passport.bilibili.com/login')
    if username is not None:
        driver.find_element_byid('login-username').sendkeys(username)

    if passwd is not None:
        driver.find_element_by_id('login-passwd').sendkeys(passwd)
        driver.find_element_by_css_selector('label[data-v-5641f300]').click()
        sleep(1)
        driver.find_element_by_css_selector('label[data-v-5641f300]').click()
        sleep(1)
        driver.find_element_by_css_selector('[class="btnbtn-login"]').click()
        xiaoliu=driver.find_element_by_css_selector('[class="item username status-box"].tips')
        xl=xiaoliu.text

        mima =driver.find_element_by_cssselector('[class="item password status-box"].tips')

        mm =mima.text
        alertText={xl:mm}
        driver.quit()
        return alertText

