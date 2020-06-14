#!/bin/python3
#! -*- coding:utf-8 -*-

__author__="edroplet"
__Date__="20200614"



'''
    https://github.com/edroplet/MyPython/tree/master/baidu   
    BDPandel.py
    该脚本是为了删除百度云盘重复的大文件。 思路是：

    将百度网盘所有文件的Md5、文件大小、名字和路径信息保存在数据库中
    根据文件的MD5来区分是否为重复文件，把路径记录下来
    根据文件的路径进行批量删除
    详细内容参考博客

    下载脚本后将数据库信息和Cookie换成自己的。

    Cookie需要有BDUSS和STOKEN的值即可。 白名单在Python脚本暂时没有添加，可以参考Java的白名单方式。

    使用方法：

    python BDPandel.py -m 1 //将文件信息入库
    python BDPandel.py -m 2 //找出重复的大文件并删除
    tbsign.py
    百度贴吧自动签到程序，将BDUSS替换为自己的BDUSS，直接运行即可。

'''

import re
from urllib import request, error, parse
import json

import pymysql
pymysql.install_as_MySQLdb()

import sys  
import argparse

from io import StringIO,BytesIO
import gzip
import os

#reload(sys)  
#sys.setdefaultencoding('utf8')   

headers = {
   'Host':"pan.baidu.com",
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language':'zh-CN,zh;q=0.9',
    'Cache-Control':'max-age=0',
    'Connection': 'keep-alive',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36',
    'Cookie':"BIDUPSID=; BDORZ=; PSTM=; BAIDUID=:FG=1; MCITY=-%3A; BCLID=; BDSFRCVID=; delPer=0; PSINO=7; BDUSS=; pan_login_way=1; PANWEB=1; STOKEN=;"
}
def createTable():
   sql = '''
         CREATE TABLE `mypan` (
         `id` BIGINT(20) UNSIGNED NOT NULL AUTO_INCREMENT,
         `size` BIGINT(20) UNSIGNED NOT NULL COMMENT '尺寸',
         `md5` VARCHAR(50) NULL DEFAULT NULL COMMENT 'md5' COLLATE 'utf8_general_ci',
         `path` VARCHAR(1024) NULL DEFAULT NULL COMMENT '路径' COLLATE 'utf8_general_ci',
         `server_filename` VARCHAR(256) NULL DEFAULT NULL COMMENT '文件名' COLLATE 'utf8_general_ci',
         PRIMARY KEY (`id`) USING BTREE,
         UNIQUE INDEX `uniq_path` (`path`) USING BTREE,
         INDEX `idx_size` (`size`) USING BTREE,
         INDEX `idx_md5` (`md5`) USING BTREE
      )
      COMMENT='百度网盘'
      COLLATE='utf8_general_ci'
      ENGINE=InnoDB
      AUTO_INCREMENT=1;
      '''
   
#解压gzip
def gzdecode(data) :
    compressedstream = BytesIO(data)
    gziper = gzip.GzipFile(fileobj=compressedstream)  
    data2 = gziper.read()   # 读取解压缩后数据 
    return data2 
    
def getbdstoken():
    res_content=r'bdstoken":"(\w*)","quota'
    url = "https://pan.baidu.com/api/loginStatus?t=%d&web=5&app_id=250528&logid=MTU5MjAxNDgzNjA4ODAuNjg2NTEzMTg3MjM3NzY5NA%3D%3D&channel=chunlei&clienttype=5" % time.now()
    try:
        req=request.Request(url,headers=headers)
        f=request.urlopen(req)
        content=f.read()
        # {"errno":0,"login_info":{"bdstoken":"","photo_url":"https://dss0.bdstatic.com/7Ls0a8Sm1A5BphGlnYG/sys/portrait/item/netdisk.1.a7332c7d.Y3qGr_Q8uozkhKMwrKxNQQ.jpg","uk":4077684364,"uk_str":"4077684364","username":"qxs820624","vip_identity":"0"},"newno":"","request_id":4226184238176181536,"show_msg":""}
        
        jcontent=json.loads(content)
        if 'login_info' in jcontent and 'bdstoken' in jcontent['login_info']:
            return jcontent['login_info']['bdstoken']
        else:
            raise Exception("not json " + content)
        #print("content", gzdecode(content))
        #r = re.compile(res_content)
        #return r.findall(content)[0]
    except Exception as e:
        print("[Error]",str(e))
        raise e
        
#startDir='/study/传智播客/代码/'  
#startFiles='/study/传智播客/代码/10_补间动画.zip'  

startDir='/apps/快递查询'
startFiles='/apps/快递查询/EMS_.txt'  

start=False
startD=False

cout=0
maxRetryTimes=3

def getFiles(dir,conn=None, cur=None, retryTimes=0):
    global startD,start,cout,maxRetryTimes
    #token=getbdstoken()
    #print("dir", dir, "token", token)
    if conn:
        if cur:
            result = None
            url = "https://pan.baidu.com/api/list?r=0.24398205252349703&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5&order=time&desc=1&showempty=0&page=1&num=2000&dir="+dir;
            req=request.Request(url,headers=headers)
            try:
                f=request.urlopen(req,timeout=5)
                #content=f.read() 
                result = json.loads(f.read())
            except Exception as e:
                print(e)
                if retryTimes > maxRetryTimes:
                    raise e
                getFiles(dir, conn, cur, retryTimes+1)
                
            if result is None:
                raise Exception("result is None")
            
            for i in result['list']:
                if(i['isdir']):
                    #print(i)
                    p = i['path']
                    #path = p.decode("utf-8")
                    if not startD:
                        if p in startDir:
                            if p == startDir:
                                print("startD=", startD, p)
                                startD=True
                        else:
                            continue
                    getFiles(parse.quote(p.encode('utf-8')), conn, cur)
                else:
                    #print type((i['path']).encode('utf-8'))
                    if startD:
                        start = True
                    elif not start and i['path'] == startFiles:
                        start=True
                        startD=True
                        
                    if start:
                        print (i['path']+'-----》'+i['md5'] + '------》'+str(i['size']) + '------》'+i['server_filename'])
                        #addDatas(i['size'], (i['md5']).encode('utf-8'), (i['path']).encode('utf-8'), (i['server_filename']).encode('utf-8'))
                        addDatas(cur, i['size'], i['md5'], i['path'], i['server_filename'])
                        cout+=1
                        if cout % 200 == 0:
                            conn.commit()
        conn.commit()
    
def addDatas(cur, size,md5,path,server_filename):
    sql = "INSERT IGNORE INTO `test`.`mypan` ( `size`, `md5`, `path`, `server_filename`) VALUES (%s, %s, %s, %s)"
    #print(sql%(size,md5,path,server_filename))
    cur.execute(sql,(size,md5,path,server_filename))

    
def getDelFilePath():
    pathlist = []
    conn= pymysql.connect(
            host='127.0.0.1',
            port = 3306,
            user='root',
            passwd='',
            db ='test',
            charset='utf8'
            ) 
    cur = conn.cursor() 
    sql1 = "select md5 from `test`.`mypan` where size > 1024*1024*5 group by md5 HAVING COUNT(md5) >1 order by md5"
    r1 = cur.execute(sql1)
    info = cur.fetchmany(r1)
    for ii in info:
        md5 = (ii[0]).encode("utf-8")
        sql2 = "select min(LENGTH(path)) from  `test`.`mypan` where md5= '%s' " % (md5)
        r2 = cur.execute(sql2)  
        info_length = cur.fetchall()
        filesize = info_length[0][0]
        sql3 = "select path from `test`.`mypan` where md5='%s' and LENGTH(path) > %s" % (md5,filesize)
        r3 = cur.execute(sql3)  
        paths = cur.fetchall()
        for path in paths:
            pathlist.append(path[0])
    cur.close()
    conn.commit()
    conn.close()
    return pathlist
    
def getFileList(pathlist):
    result = '["'
    for path in pathlist:
        
        result = result +path   +'","' 
    result = result + '**************'
    return result.replace(',"**************', "]")
    
def delFiles(filelist):
    filelist =  filelist.decode("utf-8")
    url = "https://pan.baidu.com/api/filemanager?opera=delete&async=2&onnest=fail&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5&bdstoken="+getbdstoken() #+"&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA==&clienttype=0"
    data = {
        'filelist':filelist
    }
    req=request.Request(url,headers=headers,data=parse.urlencode(data))
    f=request.urlopen(req)
    #print type(f.read())
    json_r = f.read()
    result = json.loads(json_r)
    if (result['errno']):
        print ("文件删除失败")
    else:
        print ("文件删除成功，删除成功的文件为",filelist)
        
    #result = json.loads(f.read().encode('utf-8')) 
def delJob():
    pathlist = getDelFilePath()
    filelist = getFileList(pathlist)
    delFiles(filelist)
    
if __name__ == '__main__':
    #getbdstoken()
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-m',help="method to do")
    args=parser.parse_args()
    if args.m:
        conn= pymysql.connect(
                host='127.0.0.1',
                port = 3306,
                user='root',
                passwd='',
                db ='test',
                charset='utf8'
                )
                
        if conn:
            cur = conn.cursor()
            if cur:
                if args.m == '1':
                    getFiles('/', conn, cur)
                elif args.m == '2':
                    delJob()
                else:
                    print ('error args')
                cur.close()
            conn.close()
    else:
        print (parser.print_help())
    exit(0)
    
    
    
    
'''
   
https://pan.baidu.com/api/list?r=0.24398205252349703&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5&desc=1&showempty=0&page=1&num=20&order=time&dir=%2F

{"errno":0,"guid_info":"","list":[{"server_filename":"\u6765\u81ea\uff1aKNT-AL20","privacy":0,"category":6,"unlist":0,"fs_id":388670939482157,"dir_empty":0,"server_atime":0,"server_ctime":1583988357,"local_mtime":1583988357,"size":0,"isdir":1,"share":0,"path":"\/\u6765\u81ea\uff1aKNT-AL20","local_ctime":1583988357,"server_mtime":1583988357,"empty":0,"oper_id":4077684364},{"server_filename":"movie","privacy":0,"category":6,"unlist":0,"fs_id":712412775785507,"dir_empty":0,"server_atime":0,"server_ctime":1515464842,"local_mtime":1515464842,"size":0,"isdir":1,"share":0,"path":"\/movie","local_ctime":1515464842,"server_mtime":1565942907,"empty":0,"oper_id":4077684364},{"server_filename":"\u6765\u81ea\uff1aVTR-AL00","privacy":0,"category":6,"unlist":0,"fs_id":504915964168341,"dir_empty":0,"server_atime":0,"server_ctime":1508561606,"local_mtime":1508561606,"size":0,"isdir":1,"share":0,"path":"\/\u6765\u81ea\uff1aVTR-AL00","local_ctime":1508561606,"server_mtime":1561369215,"empty":0,"oper_id":4077684364},{"server_filename":"\u6765\u81ea\uff1a\u767e\u5ea6\u6587\u5e93","privacy":0,"category":6,"unlist":0,"fs_id":1093620381610972,"dir_empty":0,"server_atime":0,"server_ctime":1560237429,"local_mtime":1560237429,"size":0,"isdir":1,"share":0,"path":"\/\u6765\u81ea\uff1a\u767e\u5ea6\u6587\u5e93","local_ctime":1560237429,"server_mtime":1560237429,"empty":0,"oper_id":0},{"server_filename":"\u6211\u7684bili","privacy":0,"category":6,"unlist":0,"fs_id":672564652831791,"dir_empty":1,"server_atime":0,"server_ctime":1557483242,"local_mtime":1557483242,"size":0,"isdir":1,"share":0,"path":"\/\u6211\u7684bili","local_ctime":1557483242,"server_mtime":1557483242,"empty":0,"oper_id":4077684364},{"server_filename":"\u6765\u81ea\uff1a\u5fae\u4fe1\u5907\u4efd","privacy":0,"category":6,"unlist":0,"fs_id":734432506420674,"dir_empty":0,"server_atime":0,"server_ctime":1550894275,"local_mtime":1550894275,"size":0,"isdir":1,"share":0,"path":"\/\u6765\u81ea\uff1a\u5fae\u4fe1\u5907\u4efd","local_ctime":1550894275,"server_mtime":1550894275,"empty":0,"oper_id":0},{"server_filename":"00\u7075\u5b9d","privacy":0,"category":6,"unlist":0,"fs_id":1087422537291631,"dir_empty":0,"server_atime":0,"server_ctime":1550407768,"local_mtime":1550407768,"size":0,"isdir":1,"share":0,"path":"\/00\u7075\u5b9d","local_ctime":1550407768,"server_mtime":1550407768,"empty":0,"oper_id":4077684364},{"server_filename":"for teaching","privacy":0,"category":6,"unlist":0,"fs_id":210060327090919,"dir_empty":0,"server_atime":0,"server_ctime":1545036469,"local_mtime":1545036469,"size":0,"isdir":1,"share":0,"path":"\/for teaching","local_ctime":1545036469,"server_mtime":1545036481,"empty":0,"oper_id":4077684364},{"server_filename":"FRM","privacy":0,"category":6,"unlist":0,"fs_id":571158453362598,"dir_empty":0,"server_atime":0,"server_ctime":1539853376,"local_mtime":1539853375,"size":0,"isdir":1,"share":0,"path":"\/FRM","local_ctime":1539853375,"server_mtime":1539853385,"empty":0,"oper_id":4077684364},{"server_filename":"\u6851\u690d\u4e00\u4e2d\u521d131\u73ed20\u5e7420120429-30","privacy":0,"category":6,"unlist":0,"fs_id":999575010728491,"dir_empty":1,"server_atime":0,"server_ctime":1539147808,"local_mtime":1539147808,"size":0,"isdir":1,"share":0,"path":"\/\u6851\u690d\u4e00\u4e2d\u521d131\u73ed20\u5e7420120429-30","local_ctime":1539147808,"server_mtime":1539147808,"empty":0,"oper_id":4077684364},{"server_filename":"\u6765\u81ea\uff1a\u767e\u5ea6App","privacy":0,"category":6,"unlist":0,"fs_id":920959998535365,"dir_empty":1,"server_atime":0,"server_ctime":1539094791,"local_mtime":1539094791,"size":0,"isdir":1,"share":0,"path":"\/\u6765\u81ea\uff1a\u767e\u5ea6App","local_ctime":1539094791,"server_mtime":1539094791,"empty":0,"oper_id":0},{"server_filename":"\u6765\u81ea\uff1aBKL-AL00","privacy":0,"category":6,"unlist":0,"fs_id":885117887096961,"dir_empty":0,"server_atime":0,"server_ctime":1519197191,"local_mtime":1519197191,"size":0,"isdir":1,"share":2,"path":"\/\u6765\u81ea\uff1aBKL-AL00","local_ctime":1519197191,"server_mtime":1528530800,"empty":0,"oper_id":4077684364},{"server_filename":"00","privacy":0,"category":6,"unlist":0,"fs_id":148456813909612,"dir_empty":0,"server_atime":0,"server_ctime":1527406328,"local_mtime":1527406328,"size":0,"isdir":1,"share":0,"path":"\/00","local_ctime":1527406328,"server_mtime":1527406328,"empty":0,"oper_id":4077684364},{"server_filename":"\u6211\u7684\u8d44\u6e90","privacy":0,"category":6,"unlist":0,"fs_id":742163895024402,"dir_empty":0,"server_atime":0,"server_ctime":1526850471,"local_mtime":1526850471,"size":0,"isdir":1,"share":0,"path":"\/\u6211\u7684\u8d44\u6e90","local_ctime":1526850471,"server_mtime":1526850471,"empty":0,"oper_id":4077684364},{"server_filename":"00\u7cbe\u54c1\u7b80\u5386\u6a21\u677f","privacy":0,"category":6,"unlist":0,"fs_id":763455222958087,"dir_empty":0,"server_atime":0,"server_ctime":1519195736,"local_mtime":1519195736,"size":0,"isdir":1,"share":0,"path":"\/00\u7cbe\u54c1\u7b80\u5386\u6a21\u677f","local_ctime":1519195736,"server_mtime":1519195931,"empty":0,"oper_id":4077684364},{"server_filename":"\u7d20\u6750","privacy":0,"category":6,"unlist":0,"fs_id":1030431281205909,"dir_empty":0,"server_atime":0,"server_ctime":1483590502,"local_mtime":1483590502,"size":0,"isdir":1,"share":0,"path":"\/\u7d20\u6750","local_ctime":1483590502,"server_mtime":1483590512,"empty":0,"oper_id":0},{"server_filename":"000000","privacy":0,"category":6,"unlist":0,"fs_id":482632101657067,"dir_empty":0,"server_atime":0,"server_ctime":1471674475,"local_mtime":1471674475,"size":0,"isdir":1,"share":0,"path":"\/000000","local_ctime":1471674475,"server_mtime":1471674475,"empty":0,"oper_id":0},{"server_filename":"\u65f6\u95f4\u7b80\u53f2","privacy":0,"category":6,"unlist":0,"fs_id":1098812636314508,"dir_empty":1,"server_atime":0,"server_ctime":1470233766,"local_mtime":1470233766,"size":0,"isdir":1,"share":0,"path":"\/\u65f6\u95f4\u7b80\u53f2","local_ctime":1470233766,"server_mtime":1470233766,"empty":0,"oper_id":0},{"server_filename":"document for work","privacy":0,"category":6,"unlist":0,"fs_id":627349822651246,"dir_empty":0,"server_atime":0,"server_ctime":1467773510,"local_mtime":1467773510,"size":0,"isdir":1,"share":0,"path":"\/document for work","local_ctime":1467773510,"server_mtime":1467773510,"empty":0,"oper_id":0},{"server_filename":"\u5185\u90e8\u6d4b\u8bd5\u7248\u672cOTT","privacy":0,"category":6,"unlist":0,"fs_id":449143869995220,"dir_empty":1,"server_atime":0,"server_ctime":1455412852,"local_mtime":1455412852,"size":0,"isdir":1,"share":0,"path":"\/\u5185\u90e8\u6d4b\u8bd5\u7248\u672cOTT","local_ctime":1455412852,"server_mtime":1455412852,"empty":0,"oper_id":0}],"request_id":3813618832595304647,"guid":0}
 
 
 

https://pan.baidu.com/api/filemanager?opera=delete&async=2&onnest=fail&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5&bdstoken=34aef459adf93855a1eb47930bb280ed

filelist: ["/共享/微信图片_20181121092434.jpg"]


https://pan.baidu.com/api/quota?t=1592014836267&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5
{"errno":0,"used":1759044092765,"total":2311766147072,"request_id":3813618827579649214}

https://pan.baidu.com/api/loginStatus?t=1592014836268&web=5&app_id=250528&logid=MTQ5NTU0ODk4Mjk2MjAuMzgyNjczNDYzNDM0MTU0NA%3D%3D&channel=chunlei&clienttype=5

{"errno":0,"login_info":{"bdstoken":"34aef5a1eb47930bb280ed","photo_url":"https://dss0.bdstatic.com/7Ls0a8Sm1A5BphGlnYG/sys/portrait/item/netdisk.1.a7332c7d.Y3qGr_Q8uozkhKMwrKxNQQ.jpg","uk":4077684364,"uk_str":"4077684364","username":"qxs820624","vip_identity":"0"},"newno":"","request_id":4226184238176181536,"show_msg":""}



'''    
            
