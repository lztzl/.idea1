print("------员工管理系统------")
print("1、添加员工信息")
print("2、删除员工信息")
print("3、查找员工信息")
print("4、修改员工信息")
print("5、输出员工信息表")
print("6、退出系统")
print("------员工管理系统-----")
employee = []
while True:
    number = int(input("请输入相应的数字进行相应的操作："))
    if number <= 0 or number > 6:
        print("输入错误！")
        break
    else:
        if number == 1:
            e_number = int(input("请通过要添加员工的数量："))
            for p in range(e_number):
                new_employee = input("请输入要添加的员工：")
                employee.append(new_employee)
            print(f"添加成功！已添加{e_number}个员工！")
        elif number == 2:
            del_employee = input("请输入要删除的员工：")
            employee.remove(del_employee)
            print(f"员工{del_employee}删除成功！")
        elif number == 3:
            search_employee = input("请输入要查找的员工：")
            if search_employee in employee:
                print("已查找到该员工！")
            else:
                print("该员工不存在！是否添加该新员工？")
                affirm = input("请输入Y/N来确认：")
                if affirm == "Y":
                    employee.append(search_employee)
                    print(f"添加成功！已添加{search_employee}员工！")
                else:
                    continue
        elif number == 4:
            mod_employee = input("请输入要修改的员工：")
            index = employee.index(mod_employee)
            moded_employee = input("请输入修改后的员工：")
            employee[index] = moded_employee
            print(f"原员工已被修改，修改后的员工为{moded_employee}")
        elif number == 5:
            for i in employee:
                print(i)
        elif number == 6:
            break