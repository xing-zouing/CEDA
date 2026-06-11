import pyparsing as _p # 使用pyparsing进行网表的语法解析
from . import netlist as nl
# 中山大学网表解析（网表中注释的匹配需去除，否则会报错）.cdl
def parse_spice(netlist_string):
    # ====================== 新增：网表预处理（核心解决所有解析问题） ======================
    lines = netlist_string.split('\n')
    clean_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 1. 跳过空行
        if not line:
            i += 1
            continue

        # 2. 跳过所有注释行（以*开头的行）
        if line.startswith('*'):
            i += 1
            continue

        # 3. 跳过所有无关的dot命令（只保留.SUBCKT和.ENDS）
        if line.startswith('.') and not line.startswith('.SUBCKT') and not line.startswith('.ENDS'):
            i += 1
            continue

        # 4. 处理续行符+：把下一行合并到当前行
        while i + 1 < len(lines) and lines[i + 1].strip().startswith('+'):
            line += ' ' + lines[i + 1].strip()[1:].strip()
            i += 1

        # 5. 删除行末尾所有多余字符（包括$$$$$、空格、制表符）
        line = line.split('$')[0].strip()

        clean_lines.append(line)
        i += 1

    # 把处理后的行重新拼接成字符串
    clean_netlist = '\n'.join(clean_lines) + '\n'

    ws = ' \t' # 换行符
    _p.ParserElement.setDefaultWhitespaceChars(ws)  # 解析器默认跳过空白字符(' \t\n') 但是换行符不能跳过 调用此方法将其从可跳过的字符集中删除换行符

    # spectre网表语法定义
    EOL = _p.LineEnd().suppress()  # 定义末尾的别名EOL
    linebreak = _p.Suppress(_p.LineEnd() + "+")  # 断行
    identifier = _p.Word(_p.alphanums + '._!<>#-+')  # 定义典型的程序变量名字name 由数字、字母、特殊符号构成，现有网表中只用到_这个特殊符号
    net = identifier  # 一个net的名字的形式 net('net')这是给它起名为net
    nets = _p.Group(_p.OneOrMore(net('net') + ~_p.FollowedBy("=") | linebreak))  #（net格式后面跟着=（但是匹配的组里不包含=）或者行结束标志）一个多个net形成nets
    cktname = identifier  # subcircuit名称
    # CaselessLiteral 匹配到的数据（排除大小写敏感） 返回到result中的结果是预定义好的type
    ckttype = _p.CaselessLiteral("type:").suppress() + identifier  # type of subcircuit: analog/digital/block
    cktname_end = _p.CaselessLiteral(".ends").suppress()

    # 每一行具体器件情况 都有一行注释comment 注释的格式是 * 开头（我们需要匹配值一行但是不需要这一行的信息所以调用了Suppress）
    comment = _p.Suppress(".PARAM" + _p.SkipTo(_p.LineEnd())) | _p.Suppress("*" + _p.SkipTo(_p.LineEnd())) #跳过网表".PARAM"行和注释行
    expression = _p.Word(_p.alphanums + '._*+-/()')  # expression的格式是数字、字母、特殊符号
    inst_param_key = identifier + _p.Suppress("=")  # inst参数的key（等号前面的项）类型
    inst_param_value = expression('expression')  # inst参数的value（等号后面的项）类型
    # 参数的格式 就是由key和value组成的 并将inst参数的的名字定义为key
    inst_parameter = _p.Group(inst_param_key('name') + inst_param_value('value')).setResultsName('key')
    # 参数组的格式
    parameters = _p.Group(_p.ZeroOrMore(inst_parameter | linebreak)).setResultsName('parameters')
    instname = identifier  # 表示网表中的每个器件和器件类型，如MM8、XR0和p33e2r、mim1_ckt等
    instnets = _p.Group(_p.OneOrMore(net('net') + ~_p.FollowedBy("=") | linebreak))  # 表示网表中各个器件的d/g/s/b的连接位置VDDA、GNDA、net12等等
    instance = _p.Group(instname('name') + instnets('instnets') + parameters + EOL).setResultsName('instance')  # 表示网表后边的沟道宽W、长L和指数M
    subcircuit_content = _p.Group(_p.ZeroOrMore(instance | EOL | comment)).setResultsName('subnetlist')  # 子电路由许多个instance 注释等组成的
    # 网表会有一个topcircuit
    topcircuit = _p.Group(
        # matches subckt <name> <nets> <newline>
        _p.CaselessLiteral(".subckt").suppress() + _p.Optional(ckttype('type')) + cktname('name') + _p.Optional(nets('nets')) + EOL
        # matches the content of the subcircuit
        + subcircuit_content
        # matches ends <name> <newline>
        + cktname_end + EOL).setResultsName('topcircuit')
    # 网表文件由top电路、EOL和注释组成
    netlist_element = topcircuit | EOL | comment('comment')
    # 整个网表文件是由多个网表文件组成
    netlist = _p.ZeroOrMore(netlist_element) + _p.StringEnd()

    # 所以需要将数据初始化（类型转换）
    parameters.setParseAction(handle_parameters)  # 解析出来的数据会以ParseResult的格式存储 需将其转换为我们自己需要的格式
    instance.setParseAction(handle_instance)
    topcircuit.setParseAction(handle_topcircuit)

    nl1 = netlist.parseString(clean_netlist)  # 根据定义好的解析方法  解析输入的网表文件
    return nl1

def handle_parameters(token):
    d = {}
    for p in token.parameters:
        d[p[0]] = p[1]
    return d

def handle_topcircuit(token):
    sc = token.topcircuit
    nets = sc.nets
    name = sc.name
    instances = sc.subnetlist
    s = nl.subcircuit(name, nets, instances)
    s.typeof = 'topcircuit'
    return [s]

def handle_instance(token):
    inst = token.instance
    name = str(inst.name)  # 显式转字符串
    # this is the case for hspice
    pins = [str(p) for p in inst.instnets[0:-1]]  # 所有引脚都转字符串
    reference = str(inst.instnets[-1])  # 器件类型转字符串（最关键！）
    parameters = inst.parameters
    i = nl.instance(name, pins, reference, parameters)
    return [i]

