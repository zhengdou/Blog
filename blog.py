import os
import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import torndb
import time
import MySQLdb
import urllib
import urllib2
import json

from markdown2 import Markdown
from tornado.options import options, define

define("port", default = "8000", help = "run in server", type = int)
define("mysql_host", default="******", help="mysql host")
define("mysql_database", default="****", help="database name")
define("mysql_user", default="******", help="mysql username")
define("mysql_password", default="****", help="mysql password")

db = torndb.Connection(host=options.mysql_host, database=options.mysql_database, user=options.mysql_user, password=options.mysql_password, charset="utf8")
PER_PAGE = 6
def md2html(content):
	return Markdown().convert(content)

def escape(strings):
	str_result = []
	result = []
	for string in strings:
		str_result.append(string.encode("utf-8"))
	for string in str_result:
		result.append(MySQLdb.escape_string(string))
	return result

class BaseHandler(tornado.web.RequestHandler):
	def get_current_user(self):
		return self.get_secure_cookie("status")
	def get(self):
		self.write_error(404)
	def write_error(self, status_code, **kwargs):
		if status_code == 404:
			self.render('404.html')

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('index.html')

class BlogHandler(tornado.web.RequestHandler):
	def get(self):
		total = db.get("SELECT COUNT(*) FROM articles")
		page_number = total['COUNT(*)']/PER_PAGE
		if total['COUNT(*)']%PER_PAGE != 0:
			page_number +=1
		page = int(self.get_argument('page', '1'))
		start = (page-1) * PER_PAGE
		articles = db.query("SELECT * FROM articles ORDER BY time DESC limit %s,%s", start, PER_PAGE)
		self.render('blog.html', articles=articles, page_number=page_number, page=page)

class ShowArticleHandler(tornado.web.RequestHandler):
	def get(self, id):
		login = self.get_secure_cookie('username')
		article = db.get("SELECT * FROM articles WHERE id=%s", id)
		comments = db.query("SELECT * FROM comments WHERE article_id=%s", id)
		child_comments = {}
		for comment in comments:
			child_comments[comment['id']] = db.query("SELECT * FROM comments WHERE comment_id=%s", comment['id'])

		self.render('article.html', article=article, comments=comments, child_comments=child_comments, login = login)

class CommentHandler(tornado.web.RequestHandler):
	def post(self):
		article_id = self.get_argument('article_id')
		comment_id = self.get_argument('comment_id')
		name = self.get_secure_cookie('username')
		head = self.get_secure_cookie('head')
		content = self.get_argument('comment')
		re = self.get_argument('re')
		time_now =  time.strftime('%Y-%m-%d %X', time.localtime())
		if comment_id == '':
			article_id, name, head, content, re = escape((article_id, name, head, content, re))
			sqlstr = "INSERT INTO comments(article_id, name, head, content, re, time) VALUES ('"+article_id+"','"+name+"','"+head+"','"+content+"','"+re+"','"+time_now+"')"
		else:
			comment_id, name, head, content, re = escape((comment_id, name, head, content, re))
			sqlstr = "INSERT INTO comments(comment_id, name, head, content, re, time) VALUES ('"+comment_id+"','"+name+"','"+head+"','"+content+"','"+re+"','"+time_now+"')"
		db.execute(sqlstr)
		self.redirect("/article/"+article_id)


class AboutHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('about.html')

class WeiboLoginHandler(BaseHandler):
        def get(self):
		error_code = self.get_argument('error_code',None)
		if error_code:
			self.redirect("/login")
		else:
			code = self.get_argument('code')
			print code
			url = 'https://api.weibo.com/oauth2/access_token?client_id=2987790593&client_secret=42fee685c15b3a317bd0b25c3bffb029&grant_type=authorization_code&redirect_uri=just4lcn.com/weibo'
			date = {'code':str(code)}
			req = urllib2.Request(url, urllib.urlencode(date))
			res = urllib2.urlopen(req)
			info = json.loads(res.read())
			print info
			access_token = info['access_token']
			uid = info['uid']
			url = "https://api.weibo.com/2/users/show.json?access_token="+access_token+"&uid="+uid
			user = urllib2.urlopen(url).read()
			user = json.loads(user)
			self.set_secure_cookie("username",user['screen_name'])
			self.set_secure_cookie("head", user['profile_image_url'])
			self.redirect(self.get_secure_cookie('url'))
           

class LoginHandler(BaseHandler):
	def get(self):
		url = self.get_argument('next', None)
		if url:
			self.set_secure_cookie('url', url)
		else:
			self.set_secure_cookie('url', '/blog')
		self.render("login.html")
	def post(self):
		name = self.get_argument("username")
		password = self.get_argument("password")
		if db.get("SELECT * FROM users WHERE name=%s and password=%s", name, password) is not None:
			self.set_secure_cookie("status",'admin')
			self.set_secure_cookie("username", name)
			self.set_secure_cookie("head", "http://www.just4lcn.com/static/images/head.png")
			self.redirect(self.get_secure_cookie('url'))
		else:
			self.redirect("/login")
class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_all_cookies()
		self.redirect("/blog")

class ManageHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		print self.get_secure_cookie('username')
		self.render('manage.html')

class NewArticleHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.render('new_article.html')
	def post(self):
		name = self.get_argument('title')
		md_content = self.get_argument('content')
		md_summary = self.get_argument('summary')
		content = md2html(md_content)
		summary = md2html(md_summary)
		name, summary, md_summary, content, md_content = escape((name, summary, md_summary, content, md_content))
		time_now =  time.strftime('%Y-%m-%d %X', time.localtime())
		sqlstr = "INSERT INTO articles(name, summary, md_summary, content, md_content, time) VALUES ('"+name+"','"+summary+"','"+md_summary+"','"+content+"','"+md_content+"','"+time_now+"')"
		db.execute(sqlstr)
		self.redirect("/blog")

class ArticleManageHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		articles = db.query("SELECT id,name,time FROM articles ORDER BY id DESC")
		self.render('article_manage.html', articles=articles)

class EditHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, id):
		article = db.get("SELECT id,name,md_summary,md_content FROM articles WHERE id=%s", id)
		self.render('edit.html', article=article)
	def post(self, id):
		name = self.get_argument('title')
		md_content = self.get_argument('content')
		md_summary = self.get_argument('summary')
		content = md2html(md_content)
		summary = md2html(md_summary)
		id, name, summary, md_summary, content, md_content = escape((id, name, summary, md_summary, content, md_content))
		sqlstr = "UPDATE articles SET name='"+name+"', summary='"+summary+"', md_summary='"+md_summary+"', content='"+content+"', md_content='"+md_content+"' WHERE id='"+id+"'"
		db.execute(sqlstr)
		self.redirect("/article/"+id)

class DeleteArticleHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self,id):
		db.execute('DELETE FROM articles WHERE id=%s',id)
		db.execute('DELETE FROM comments WHERE article_id=%s',id)
		self.redirect("/article-manage")

class ExportHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self,id):
		lineend = os.linesep
		article = db.get("SELECT name,md_content FROM articles WHERE id=%s", id)
		name, content = escape((article['name'], article['md_content']))
		content = content.split('\\r\\n')
		result = ''
		for item in content:
			result += item+lineend
		file_name = name+'.md'
		file = os.path.join(os.getcwd(),"static","article",file_name)
		with open(file,'w') as f:
			f.write(result)
		self.redirect("/static/article/"+file_name)

class CommentManageHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		comments = db.query("SELECT * FROM comments ORDER BY time DESC")
		self.render("comment_manage.html", comments=comments)

class DeleteCommentHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self, id):
		db.execute('DELETE FROM comments WHERE id=%s',id)
		db.execute('DELETE FROM comments WHERE comment_id=%s',id)
		self.redirect("/comment-manage")




handlers = [(r'/', IndexHandler),
			(r'/blog', BlogHandler),
			(r'/about', AboutHandler),
			(r'/article/(\d+)', ShowArticleHandler),
			(r'/comment', CommentHandler),
			(r'/manage', ManageHandler),
			(r'/new-article', NewArticleHandler),
			(r'/article-manage', ArticleManageHandler),
			(r'/edit/(\d+)', EditHandler),
			(r'/delete-article/(\d+)', DeleteArticleHandler),
			(r'/export/(\d+)', ExportHandler),
			(r'/comment-manage', CommentManageHandler),
			(r'/delete-comment/(\d+)', DeleteCommentHandler),
			(r'/login', LoginHandler),
			(r'/logout', LogoutHandler),
            (r'/weibo', WeiboLoginHandler),
            (r'.*', BaseHandler)]


if __name__ == '__main__':
	tornado.options.parse_command_line()
	settings = {"template_path":os.path.join(os.path.dirname(__file__), "templates"),
				"static_path":os.path.join(os.path.dirname(__file__), "static"),
				"xsrf_cookies": True,
				"cookie_secret":"G2m7BmK6T0a8i3WXPM0GekTHuCZ2pEqQskpxqdgOE+A=",
				"login_url":"/login"
	}
	app = tornado.web.Application(handlers=handlers, **settings)
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()
