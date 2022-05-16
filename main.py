def get_level(cource):
    """
    自定义的方法
    :param cource:成绩
    :return:
    """
    if cource >= 90:
        return "优秀"
    elif cource >= 80:
       return "良好"
    elif cource >= 60:
        return "合格"
    elif cource >= 40:
        return "不合格"
    else:
        return "差"