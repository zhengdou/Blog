*环境 ubuntu 16.04 *
###supervisor
安装supervisor  
```
sudo apt-get install supervisor
```  
导入supervisor配置文件（需以root身份运行，不是sudo，而是进入root切换到root用户）  
```
echo_supervisord_conf > /etc/supervisord.conf
```  
编辑该文件  
```
vim /etc/supervisord.conf
```  
在文件最后加入配置项  

    [program:blog]   
    command=python /home/blog/blog.py  
    directory=/home/blog  
    autorestart=true  
    redirect_stderr=true  

根据需要跟换program名称和command即可  
启动supervisor并启动该进程  

    sudo supervisord  
    sudo supervisorctl start blog  #blog为之前配置文件里program名称  

supervisorctl 基本命令：   
1.启动：start [name]  
2.停止：stop [name]  
3.重启：restart [name]  
4.管理所有进程 使用 all 代替name  
###nginx  
安装  
```
sudo apt-get install nginx
```  
启动nginx  
```
sudo service nginx start
```  
启动成功则没有问题  
在/etc/nginx/site-avaliable目录下创建配置文件 blog.conf
输入  

    upstream blog  
    {  
        server 127.0.0.1:8000;  
    }   
    server  
    {  
        listen 80;  
        server_name just4lcn.com www.just4lcn.com;   #本地改为 localhost即可
        location /static/ {  
            root /var/www/static;  #static目录
            if ($query_string) {  
                expires max;  
            }  
        }  
        location ~/ {  
            proxy_pass_header Server;  
            proxy_set_header Host $http_host;  
            proxy_redirect off;  
            proxy_set_header X-Real-IP $remote_addr;  
            proxy_set_header X-Scheme $scheme;  
            proxy_pass http://blog;  
        }      
    }  

将该文件链接到 site-enabled目录下  
```
sudo ln -s /etc/nginx/sites-available/blog.conf /etc/nginx/sites-enabled/blog.conf  
```  
删除 site-avaliable下default文件  
重启 nginx  
```
sudo service nginx reload
```  
```
sudo service nginx restart
```  
配置完成
