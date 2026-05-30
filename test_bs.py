import re

s1 = '\begin' # length 6
s2 = '\\begin' # length 6
s3 = '\\\\begin' # length 7

print("s2 matches r'\\\\begin':", bool(re.search(r'\\begin', s2)))
print("s2 matches r'\\\\\\\\begin':", bool(re.search(r'\\\\begin', s2)))

latex_str = r'|a| = \begin{cases} a & \text{if } a \ge 0 \\ -a & \text{if } a < 0 \end{cases}'
print("latex_str matches my regex:", bool(re.search(r'\\begin\{cases\}(.*?)\\end\{cases\}', latex_str, re.DOTALL)))
