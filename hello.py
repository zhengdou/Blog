import os
import os.path
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import torndb
import time
import MySQLdb

from markdown2 import Markdown
from tornado.options import options, define

define("port", default = "8000", help = "run in server", type = int)
define("mysql_host", default="127.0.0.1:3306", help="mysql host")
define("mysql_database", default="blog", help="database name")
define("mysql_user", default="root", help="mysql username")
define("mysql_password", default="930614", help="mysql password")

db = torndb.Connection(host=options.mysql_host, database=options.mysql_database, user=options.mysql_user, password=options.mysql_password, charset="utf8")

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

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('index.html')

class BlogHandler(tornado.web.RequestHandler):
	def get(self):
		articles = db.query("SELECT * FROM articles ORDER BY time DESC")
		self.render('blog.html', articles=articles)

class ShowArticleHandler(tornado.web.RequestHandler):
	def get(self, id):
		article = db.get("SELECT * FROM articles WHERE id=%s", id)
		comments = db.query("SELECT * FROM comments WHERE article_id=%s", id)
		child_comments = {}
		for comment in comments:
			child_comments[comment['id']] = db.query("SELECT * FROM comments WHERE comment_id=%s", comment['id'])

		self.render('article.html', article=article, comments=comments, child_comments=child_comments)

class CommentHandler(tornado.web.RequestHandler):
	def post(self):
		article_id = self.get_argument('article_id')
		comment_id = self.get_argument('comment_id')
		name = self.get_argument('name')
		email = self.get_argument('email')
		content = self.get_argument('comment')
		re = self.get_argument('re')
		time_now =  time.strftime('%Y-%m-%d %X', time.localtime())
		if comment_id == '':
			article_id, name, email, content , re = escape((article_id, name, email, content, re))
			sqlstr = "INSERT INTO comments(article_id, name, email, content, re, time) VALUES ('"+article_id+"','"+name+"','"+email+"','"+content+"','"+re+"','"+time_now+"')"
		else:
			comment_id, name, email, content = escape((comment_id, name, email, content))
			sqlstr = "INSERT INTO comments(comment_id, name, email, content, re, time) VALUES ('"+comment_id+"','"+name+"','"+email+"','"+content+"','"+re+"','"+time_now+"')"
		db.execute(sqlstr)
		self.redirect("/article/"+article_id)


class AboutHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('about.html')

class ManageHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('manage.html')

class NewArticleHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('new_article.html')
	def post(self):
		name = self.get_argument('title')
		md_content = self.get_argument('content')
		content = md2html(md_content)
		name, content, md_content = escape((name, content, md_content))
		summary = content
		time_now =  time.strftime('%Y-%m-%d %X', time.localtime())
		sqlstr = "INSERT INTO articles(name, summary, content, md_content, time) VALUES ('"+name+"','"+summary+"','"+content+"','"+md_content+"','"+time_now+"')"
		db.execute(sqlstr)
		self.redirect("/blog")

class ArticleManageHandler(tornado.web.RequestHandler):
	def get(self):
		articles = db.query("SELECT id,name,time FROM articles ORDER BY id DESC")
		self.render('article_manage.html', articles=articles)

class EditHandler(tornado.web.RequestHandler):
	def get(self, id):
		article = db.get("SELECT id,name,md_content FROM articles WHERE id=%s", id)
		self.render('edit.html', article=article)
	def post(self, id):
		name = self.get_argument('title')
		md_content = self.get_argument('content')
		content = md2html(md_content)
		id, name, content, md_content = escape((id, name, content, md_content))
		summary = content
		sqlstr = "UPDATE articles SET name='"+name+"', summary='"+summary+"', content='"+content+"', md_content='"+md_content+"' WHERE id='"+id+"'"
		db.execute(sqlstr)
		self.redirect("/article/"+id)

class DeleteArticleHandler(tornado.web.RequestHandler):
	def get(self,id):
		db.execute('DELETE FROM articles WHERE id=%s',id)
		db.execute('DELETE FROM comments WHERE article_id=%s',id)
		self.redirect("/article-manage")

class ExportHandler(tornado.web.RequestHandler):
	def get(self,id):
		lineend = os.linesep
		article = db.get("SELECT name,md_content FROM articles WHERE id=%s", id)
		name, content = escape((article['name'], article['md_content']))
		content = content.split('\\r\\n')
		result = ''
		for item in content:
			result += item+lineend
		print content
		file_name = name+'.md'
		file = os.path.join(os.getcwd(),"static","article",file_name)
		with open(file,'w') as f:
			f.write(result)
		self.redirect("/static/article/"+file_name)

class CommentManageHandler(tornado.web.RequestHandler):
	def get(self):
		comments = db.query("SELECT * FROM comments ORDER BY time DESC")
		self.render("comment_manage.html", comments=comments)

class DeleteCommentHandler(tornado.web.RequestHandler):
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
			(r'/delete-comment/(\d+)', DeleteCommentHandler)]


if __name__ == '__main__':
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=handlers, 
		template_path=os.path.join(os.path.dirname(__file__), "templates"),
		static_path=os.path.join(os.path.dirname(__file__), "static"))
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()