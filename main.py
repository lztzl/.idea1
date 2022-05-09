class Employee:
    def __init__(self, name, gender, department, post):
        self.name = name # 姓名
        self.gender = gender # 性别
        self.department = department # 所在部门
        self.post = post # 职称
        from prettytable import PrettyTable

        class EmployeeManageSystem:
            def __init__(self):
                # self.employee_info 用来存储每个员工对象
                self.employee_info = []

            def menu(self):
                """ 展示系统目录 """
                print('=' * 25, '欢迎来到员工管理系统', '=' * 25)
                print('%s%s' % ('1. 增加员工信息'.center(33), '2. 删除员工信息'.center(33)))
                print('%s%s' % ('3. 查看员工信息'.center(33), '4. 修改员工信息'.center(33)))
                print('%s' % '5. 退出系统'.center(32))
                print('=' * 72)

            def add_employee(self):
                """ 用于增加员工信息 """
                while True:
                    print('-' * 29, '增加员工信息', '-' * 29)
                    name = input('输入员工姓名：')
                    gender = input("输入员工性别：")
                    department = input("输入员工所在部门：")
                    post = input("输入员工职位名称：")
                    employee = Employee(name, gender, department, post)
                    self.employee_info.append(employee)
                    print('已添加')
                    if input('是否继续?按n键结束').lower() == 'n':
                        break

            def show_employee_info(self):
                """ 显示所有员工信息 """
                print('-' * 29, '查看员工信息', '-' * 29)
                table = PrettyTable()
                table.field_names = ['序号', '姓名', '性别', '所在部门', '职位名称']
                for index, i in enumerate(self.employee_info):
                    table.add_row([index + 1, i.name, i.gender, i.department, i.post])
                print(table, end='\n\n')
                del table

            def delete_employee(self):
                """ 删除员工 """
                while True:
                    self.show_employee_info()
                    print('-' * 29, '删除员工信息', '-' * 29)
                    index = int(input('输入要删除的员工的序号: '))
                    del self.employee_info[index - 1]
                    print('已删除')
                    if input('是否继续?按n键结束').lower() == 'n':
                        break

            def update_employee_info(self):
                """ 用于修改员工信息 """
                while True:
                    print('-' * 29, '修改员工信息', '-' * 29)
                    self.show_employee_info()
                    index = int(input('输入要修改的员工的序号：')) - 1
                    print('1.姓名\t 2.性别\t 3.所在部门\t 4.职位名称')
                    option = input('输入要修改的序号：')

                    if option == '1':
                        self.employee_info[index].name = input('请输入姓名：')
                    elif option == '2':
                        self.employee_info[index].gender = input('请输入性别：')
                    elif option == '3':
                        self.employee_info[index].department = input('请输入所在部门：')
                    else:
                        self.employee_info[index].post = input('请输入职位名称：')

                    print('已修改')
                    if input('是否继续?按n键结束').lower() == 'n':
                        break

employee_manage_system = EmployeeManageSystem()
while True:
    employee_manage_system.menu()
    index = input('选择相应的序号：')
    if index == '5':
        break
    option_list = {'1': employee_manage_system.add_employee, '2': employee_manage_system.delete_employee,
                   '3': employee_manage_system.show_employee_info, '4': employee_manage_system.update_employee_info}
    try:
        option_list[index]()
    except:
        print('输入出现问题，请重试!\n')



