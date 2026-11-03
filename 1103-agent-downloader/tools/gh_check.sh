#!/bin/bash
# [A03] 验证 GitHub token 与 lishuhang/clock 仓库访问/推送权限
TOK=$(cat /home/z/my-project/.secrets/github_token)
echo "== token /user =="
curl -s -m 10 -H "Authorization: token $TOK" https://api.github.com/user | python3 -c "import json,sys;d=json.load(sys.stdin);print('login:',d.get('login'));print('message:',d.get('message'))"
echo "== rate_limit =="
curl -s -m 10 -H "Authorization: token $TOK" https://api.github.com/rate_limit | python3 -c "import json,sys;d=json.load(sys.stdin);c=d['resources']['core'];print('core:',c['remaining'],'/',c['limit'])"
echo "== repo lishuhang/clock =="
curl -s -m 10 -H "Authorization: token $TOK" https://api.github.com/repos/lishuhang/clock | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k in ['full_name','default_branch','private','size','pushed_at','message']:
    print(k+':',d.get(k))
print('permissions:',d.get('permissions'))
"
