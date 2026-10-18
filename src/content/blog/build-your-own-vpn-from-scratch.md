---
title: 从零自建科学上网：写给完全零基础小白的完整教程
date: 2026-09-20
description: 一篇讲完：买 VPS、远程登录、安全加固、建站、申请证书、Xray 服务端与客户端，全部命令可直接照抄。
tags:
  - 科学上网
  - VPS
  - Xray
  - 教程
---

从输入第一条命令，到手机电脑真正连上网络，一篇讲完。方法来自 XTLS 社区的经典教程《小小小白话文》（原作者 [@ricuhkaen](https://github.com/ricuhkaen)），我按自己踩坑的理解重新组织，所有命令可直接照抄。

写给完全零基础、且想自己动手的人。已有 Linux 经验或打算用机场的同学，跳过这篇没有任何损失。

先回答"为什么要自建"。机场能用，但它有真实的风险：你的全部流量必然经过机场服务器，隐私无协议保障；市场无监管，跑路年年有；线路质量全凭良心。自建是把这几样攥回自己手里，代价是要学一点 Linux。是否值得，你自己权衡——教程按"你已决定自建"来写。

你需要准备：一台能正常用、IP 未被墙的 VPS（装 Debian 系统，记下 IP、SSH 端口、用户名、密码），一个国际域名（加 A 记录指向 VPS，`.cn` 后缀别用），本地电脑装 [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html)、[WinSCP](https://winscp.net/eng/index.php)、[VSCode](https://code.visualstudio.com)（macOS/Linux 自带 Terminal 即可）。教程里 `100.200.300.400` 和 `a-name.yourdomain.com` 都是占位符，替换成你自己的。

---

## 一、远程登录

用 PuTTY 登录（macOS/Linux 直接 `ssh` 命令，后续操作相同）：

1. 官网下载安装 PuTTY（64 位）
2. 填入 IP 和端口，Saved Sessions 里存一个会话名
3. `Connection` → `keepalive` 设为 `60`，防止空闲断线
4. 点 Open，输入用户名密码登录

注意两件事：PuTTY 任何设置改动都要重新保存 Session，否则关闭即丢；登录输密码时屏幕不显示任何字符，这是防偷窥设计，不是键盘坏了。

登录后会看到 `root@vps-server:~#` 这样的提示符：当前用户、服务器名、所在目录（`~` 是用户主目录）、命令输入位置。教程里的命令都以 `#` 或 `$` 开头，那是提示符，复制时不要带上。

然后更新系统软件。Linux 里每个软件叫"包"，Debian 的包管理器叫 `apt`：

```
apt update    # 查询有哪些更新
apt upgrade   # 执行更新，中途问 Y/n 时输入 y 回车
```

## 二、安全防护

默认设置下，登录四要素（IP、端口、用户名、密码）里有三个是公开的：IP 藏不住，端口默认 22，用户名默认 root。安全全押在密码上，而自动化脚本手握几百万条泄露密码的字典，24 小时不停尝试。一旦得手，它拿到最高权限，用你的机器挖矿、发垃圾邮件——买 VPS 用的真实支付信息意味着这些坏事最后都算在你头上。

对策三步，按顺序做，别把自己锁在门外。

### 第一步：改端口

```
nano /etc/ssh/sshd_config
```

nano 快捷键都显示在屏幕底部。用 `ctrl+w` 搜索 `Port 22`，把 22 改成 1024–65535 之间的数字（示例用 9753，建议换成你自己的，教程示例端口会成为攻击者优先尝试的特征）。行首有 `#` 说明未生效，删掉即可。保存是 `ctrl+o` 回车，退出是 `ctrl+x`。

Ubuntu 若启用了 ufw 防火墙，放行新端口：

```
sudo ufw allow 9753/tcp
```

重启 SSH 生效，然后开新会话验证，旧会话先留着兜底：

```
systemctl restart ssh
```

### 第二步：新建用户，禁用 root

root 是 Linux 的根基，它出事系统就任人摆布。新建一个普通用户（示例用 vpsadmin，建议换名）：

```
adduser vpsadmin
```

按提示设密码，附加信息一路回车。安装 sudo（让普通用户临时借用 root 权限）：

```
apt update && apt install sudo
```

把 vpsadmin 加进 sudo 名单：

```
visudo
```

在 `User Privilege Specification` 下加一行：

```
vpsadmin ALL=(ALL) NOPASSWD: ALL
```

NOPASSWD 表示用 sudo 时不再输密码。这与常规安全建议相反，但很多新人坚持用 root 就是嫌 sudo 麻烦——两害相权，直接用 root 的风险更大。介意的话改成 `vpsadmin ALL=(ALL:ALL) ALL`，每次输密码，同样可以。

禁用 root 远程登录：

```
sudo nano /etc/ssh/sshd_config
```

搜索 `PermitRootLogin` 改为 `no`，保存退出后重启：

```
sudo systemctl restart ssh
```

### 第三步：密钥登录，禁用密码

密码可能被字典撞破，密钥不会。原理：生成一对公钥私钥，公钥放服务器，私钥留本地，登录时自动匹配。

密钥选型：演示用 RSA（兼容性最好，注意要 3072 位）；设备支持的话更推荐 Ed25519，密钥短、速度快。DSA 已被证明不安全，别用。

生成：打开 PuTTYgen → Generate（晃鼠标收集随机数）→ 可给私钥设一层密码 → Save public key / Save private key。再把界面顶部的公钥文本完整复制出来，存成 `authorized_keys` 文件（VSCode 会加 .txt 后缀，上传时去掉）。

上传公钥用 WinSCP：装好后一键导入 PuTTY 会话，右侧定位到 `/home/vpsadmin/`（点右下角显示隐藏文件），新建 `.ssh` 文件夹，把 authorized_keys 传进去并去掉后缀。

回到 SSH，设置权限并改配置（现在不是 root 了，命令要加 sudo）：

```
chmod 600 ~/.ssh/authorized_keys
```

```
sudo nano /etc/ssh/sshd_config
```

搜索 `PasswordAuthentication` 改 `no`，`PubkeyAuthentication` 改 `yes`，保存退出，重启：

```
sudo systemctl restart ssh
```

最后在 PuTTY 的 Connection → SSH → Auth 里指定私钥文件，保存 Session；WinSCP 也做对应密钥设置。至此四要素加固完毕。

## 三、搭一个网站

为什么要先建站：申请 TLS 证书需要它，同时给代理流量提供合理的回落、防主动探测，域名直接访问时也有个正常前台。

装 Nginx：

```
sudo apt update && sudo apt install nginx
```

浏览器访问 `http://100.200.300.400` 看到 Nginx 欢迎页即成功。打不开就检查防火墙：

```
sudo ufw status
sudo ufw allow 'Nginx Full'
```

建网页（内容越普通越好）：

```
mkdir -p ~/www/webpage/ && nano ~/www/webpage/index.html
```

```html
<html>
<head>
  <title>My Blog</title>
</head>
<body>
  <h1>Hello</h1>
  <p>Just a quiet little page.</p>
</body>
</html>
```

保存退出，加上其他用户的读取权限：

```
chmod -R a+r .
```

告诉 Nginx 把 80 端口的访问指向这个页面：

```
sudo nano /etc/nginx/nginx.conf
```

在 `http{}` 内加一段（`server_name` 和 `root` 换成你的域名和路径）：

```
server {
        listen 80;
        server_name a-name.yourdomain.com;
        root /home/vpsadmin/www/webpage;
        index index.html;
}
```

```
sudo systemctl reload nginx
```

访问 `http://a-name.yourdomain.com` 能看到页面就成功了。打不开通常是两类问题：nginx.conf 里的路径与实际路径不符，或 Nginx 没权限读。注意 `~` 对非 root 用户等价于 `/home/你的用户名`，对 root 是 `/root`——不是 vpsadmin 用户却照抄教程命令，路径就对不上。

## 四、申请证书

TLS 证书是整套方案安全性的地基。别用自签证书，省的小事换来中间人攻击的风险。工具用 [acme.sh](https://github.com/acmesh-official/acme.sh)，能自动续期。

安装：

```
wget -O -  https://get.acme.sh | sh
. .bashrc
acme.sh --upgrade --auto-upgrade
```

先申请测试证书——配置有错时反复申请正式证书会撞上 Let's Encrypt 的频率限制（每小时每域名失败 5 次）：

```
acme.sh --issue --server letsencrypt_test -d a-name.yourdomain.com -w /home/vpsadmin/www/webpage --keylength ec-256
```

看到 `Cert success` 即配置正确（发证域名带 `staging` 就是测试服）。测试证书不用删，会被正式证书覆盖。出错就加 `--debug` 重跑看日志。

教程用 ECC 证书（`ec-256`）：密钥更短，强度约等于 RSA 3072 位，没有理由不用。要兼容极老设备才考虑 RSA。

切到正式服申请：

```
acme.sh --set-default-ca --server letsencrypt
```

```
acme.sh --issue -d a-name.yourdomain.com -w /home/vpsadmin/www/webpage --keylength ec-256 --force
```

`--force` 是因为测试证书未到期，需要强行更新。之后安装到指定位置供程序引用：

```
acme.sh --installcert -d a-name.yourdomain.com --cert-file /你要安装到的位置/cert.crt --key-file /你要安装到的位置/cert.key --fullchain-file /你要安装到的位置/fullchain.crt --ecc
```

acme.sh 之后每天自动检查，证书有效期短于 30 天自动续，不用再管。

## 五、Xray 服务端

先明确概念：Xray 的本体是 [xray-core](https://github.com/XTLS/Xray-core) 的二进制程序，放服务器跑就是服务端，放本地跑就是客户端，区别只在配置。

安装（官方脚本对非 root 用户有些小问题，拆步执行，顺便说下删除命令）：

```
wget https://github.com/XTLS/Xray-install/raw/main/install-release.sh
sudo bash install-release.sh
rm ~/install-release.sh
```

rm 默认删当前目录下的文件，但建议始终写完整路径——删库跑路的段子都听过。

### 配置证书

按 acme.sh 官方建议，证书要安装拷贝后使用，不直接引用原始位置：

```
mkdir ~/xray_cert
```

```
acme.sh --install-cert -d a-name.yourdomain.com --ecc \
            --fullchain-file ~/xray_cert/xray.crt \
            --key-file ~/xray_cert/xray.key
chmod +r ~/xray_cert/xray.key
```

之后证书自动续期、Xray 自动热重载，这条链路不用再管。

### 写配置文件

生成 UUID（几乎不会重复的身份 ID）：

```
xray uuid
```

建日志文件：

```
mkdir ~/xray_log
touch ~/xray_log/access.log && touch ~/xray_log/error.log
chmod a+w ~/xray_log/*.log
```

日志放这里是避免权限问题，熟悉后建议回归默认位置 `/var/log/xray/`。

创建配置文件：

```
sudo nano /usr/local/etc/xray/config.json
```

贴入以下内容，UUID 填进 `"id"`：

```json
{
  "log": {
    "loglevel": "warning",
    "access": "/home/vpsadmin/xray_log/access.log",
    "error": "/home/vpsadmin/xray_log/error.log"
  },
  "dns": {
    "servers": [
      "https+local://1.1.1.1/dns-query",
      "localhost"
    ]
  },
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "ip": ["geoip:private"],
        "outboundTag": "block"
      },
      {
        "ip": ["geoip:cn"],
        "outboundTag": "block"
      },
      {
        "domain": ["geosite:category-ads-all"],
        "outboundTag": "block"
      }
    ]
  },
  "inbounds": [
    {
      "port": 443,
      "protocol": "vless",
      "settings": {
        "users": [
          {
            "id": "把你生成的UUID填在这里",
            "flow": "xtls-rprx-vision",
            "level": 0,
            "email": "vpsadmin@yourdomain.com"
          }
        ],
        "decryption": "none",
        "fallbacks": [
          {
            "dest": 80
          }
        ]
      },
      "streamSettings": {
        "method": "tcp",
        "security": "tls",
        "tlsSettings": {
          "alpn": "http/1.1",
          "certificates": [
            {
              "certificateFile": "/home/vpsadmin/xray_cert/xray.crt",
              "keyFile": "/home/vpsadmin/xray_cert/xray.key"
            }
          ]
        }
      }
    }
  ],
  "outbounds": [
    {
      "tag": "direct",
      "protocol": "freedom"
    },
    {
      "tag": "block",
      "protocol": "blackhole"
    }
  ]
}
```

配置固定五个部分：log 日志、dns 查询、routing 分流、inbounds 入站、outbounds 出站。这份配置的策略：内网、国内 IP、广告域名进黑洞；443 收 VLESS+XTLS 代理流量，其余回落到 80 端口的伪装网站。

### 启动

```
sudo systemctl start xray
sudo systemctl status xray
```

看到绿色 `active (running)` 即成功。systemd 系列命令顺带认全：`start` 启动、`stop` 停止、`restart` 重启、`reload` 重读配置、`enable`/`disable` 开机自启开关，均加 `sudo`。

### 优化：开启 BBR

BBR 是 TCP 拥塞控制算法，相当于给数据流量做交通调度，速度和稳定性一般有可感知改善，建议开启。注意 bbrplus、魔改 BBR 这类脚本只是换掉你的内核，那点性能差异不值得引入不稳定的内核；跟着发行版更新内核即可。锐速、LotServer 这类"加速工具"原理是多倍发包，浪费流量，别用。

```
sudo nano /etc/sysctl.d/99-bbr.conf
```

写入：

```
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
```

生效并验证：

```
sudo sysctl --system
sysctl net.ipv4.tcp_congestion_control
```

返回 `net.ipv4.tcp_congestion_control = bbr` 即成功。

### 优化：HTTP 跳转 HTTPS

编辑 nginx.conf，在 80 端口的 server 块里加一行跳转（root、index 两行可删）：

```
return 301 https://$http_host$request_uri;
```

同级再加一个本地监听给伪装网页用：

```
server {
   listen 127.0.0.1:8080;
   root /home/vpsadmin/www/webpage;
   index index.html;
   add_header Strict-Transport-Security "max-age=63072000" always;
}
```

重启 Nginx，然后把 Xray 配置里的 `"dest": 80` 改成 `"dest": 8080`，重启 Xray：

```
sudo systemctl restart nginx
sudo nano /usr/local/etc/xray/config.json
sudo systemctl restart xray
```

更丰富的回落玩法参考官方文档 fallbacks 篇。另外网上旧版教程把 config.json 路径写错过，正确位置是 `/usr/local/etc/xray/config.json`——Xray 起不来先查这个。

## 六、Xray 客户端

先理解流量走向：APP 把数据交进 Xray 客户端（入站）→ 客户端路由按规则分流（国内直连、国外转发 VPS、广告屏蔽）→ 转发流量穿墙进入服务端 → 服务端路由后默认直连出站。借助 geosite.dat 和 geoip.dat，路由可按域名和 IP 精细控制，比老式 GFWList 灵活得多。

对照服务端 config.json，客户端需要的连接要素：

- 地址：`a-name.yourdomain.com`
- 端口：`443`
- 协议：`vless`
- 流控：`xtls-rprx-vision`
- 用户 ID：服务端填的 UUID
- 安全：TLS，禁止不安全证书

常用客户端，按平台任选，把上述要素填进对应位置：

- **v2rayN**（Windows）：[GitHub Release](https://github.com/2dust/v2rayN/releases)
- **v2rayNG**（Android）：[GitHub Release](https://github.com/2dust/v2rayNG/releases)
- **Shadowrocket**（iOS / M 芯片 Mac）：需非中国区 iCloud 账号
- **Qv2ray**（跨平台）：[GitHub Release](https://github.com/Qv2ray/Qv2ray/releases)
- **V2RayXS**（macOS）：[GitHub Release](https://github.com/tzmax/v2rayXS/releases)

注意很多工具同时支持 xray-core 和 v2fly-core 两个内核，确认实际生效的是哪个。到这一步整套自建已经可用。

### 附加：PC 上直接跑 xray-core

不用 GUI 客户端、直接跑 xray-core 的好处：第一时间用上最新版、路由配置完全自由、省资源。从 [Xray-core Release](https://github.com/XTLS/Xray-core/releases) 下载对应平台版本，旁边新建空白 `config.json`，填入：

```json
{
  "log": {
    "loglevel": "warning"
  },
  "dns": {
    "servers": [
      {
        "address": "1.1.1.1",
        "domains": ["geosite:geolocation-!cn"]
      },
      {
        "address": "223.5.5.5",
        "domains": ["geosite:cn"],
        "expectIPs": ["geoip:cn"]
      },
      {
        "address": "114.114.114.114",
        "domains": ["geosite:cn"]
      },
      "localhost"
    ]
  },
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "domain": ["geosite:category-ads-all"],
        "outboundTag": "block"
      },
      {
        "domain": ["geosite:cn"],
        "outboundTag": "direct"
      },
      {
        "domain": ["geosite:geolocation-!cn"],
        "outboundTag": "proxy"
      },
      {
        "ip": ["223.5.5.5"],
        "outboundTag": "direct"
      },
      {
        "ip": ["geoip:cn", "geoip:private"],
        "outboundTag": "direct"
      }
    ]
  },
  "inbounds": [
    {
      "tag": "socks-in",
      "protocol": "socks",
      "listen": "127.0.0.1",
      "port": 10800,
      "settings": {
        "udp": true
      }
    },
    {
      "tag": "http-in",
      "protocol": "http",
      "listen": "127.0.0.1",
      "port": 10801
    }
  ],
  "outbounds": [
    {
      "tag": "proxy",
      "protocol": "vless",
      "settings": {
        "address": "a-name.yourdomain.com",
        "port": 443,
        "id": "你的UUID",
        "flow": "xtls-rprx-vision",
        "encryption": "none",
        "level": 0
      },
      "streamSettings": {
        "method": "tcp",
        "security": "tls",
        "tlsSettings": {
          "serverName": "a-name.yourdomain.com",
          "allowInsecure": false,
          "fingerprint": "chrome"
        }
      }
    },
    {
      "tag": "direct",
      "protocol": "freedom"
    },
    {
      "tag": "block",
      "protocol": "blackhole"
    }
  ]
}
```

要点：转发 VPS 的 outbound 必须放第一位——不匹配任何路由规则的流量默认走第一个 outbound；`fingerprint: chrome` 用 uTLS 模拟 Chrome 指纹，不易被识别。

运行（`-c` 指定配置文件路径）：

Windows：

```
C:\Xray-windows-64\xray.exe -c C:\Xray-windows-64\config.json
```

macOS / Linux：

```
/usr/local/bin/xray -c /usr/local/etc/xray/config.json
```

缺点是多个黑窗口且不能开机自启，两个问题都可解决，线索在文档站问答区。

## 七、附录：速查表

Xray 起不来，按这个顺序查：配置文件路径（`/usr/local/etc/xray/config.json`）、证书权限（`chmod +r`）、日志权限（`chmod a+w`）、UUID 填了没。九成问题在这四处。

| 命令 | 用途 | 出处 |
| --- | --- | --- |
| `apt update` / `apt upgrade` | 更新软件 | 远程登录 |
| `nano` | 文本编辑器 | 安全防护 |
| `systemctl restart/reload` | 重启/重载服务 | 全篇 |
| `adduser` | 新增用户 | 安全防护 |
| `apt install` | 安装软件 | 安全防护 |
| `visudo` | 编辑 sudo 权限 | 安全防护 |
| `sudo` | 以 root 权限执行 | 安全防护 |
| `chmod` | 修改文件权限 | 安全防护 |
| `mkdir` / `touch` | 新建文件夹/空文件 | 建站/服务端 |
| `wget` | 下载文件 | 证书/服务端 |
| `acme.sh` | 证书管理 | 证书 |
| `rm` | 删除（慎用，写全路径） | 服务端 |
| `reboot` | 重启系统 | 服务端 |

| 配置/文件 | 说明 |
| --- | --- |
| `/etc/ssh/sshd_config` | SSH 设置 |
| `/etc/nginx/nginx.conf` | Nginx 设置 |
| `/etc/sysctl.d/99-bbr.conf` | BBR 内核参数 |
| `/usr/local/etc/xray/config.json` | Xray 配置 |
| `~/xray_cert/xray.crt` `xray.key` | TLS 证书/私钥 |
| `~/xray_log/access.log` `error.log` | Xray 日志 |

走完全程，你对 Linux 应该不再恐惧——这份不恐惧比翻墙本身值钱。Xray 还有路由、回落、负载均衡等更多玩法，够用就享受，好奇就去[官方文档](https://xtls.github.io/)和[Telegram 群](https://t.me/projectXray)继续挖。
