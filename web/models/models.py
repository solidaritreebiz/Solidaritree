import logging

import urllib
import httplib2
import simplejson
import yaml

from datetime import datetime

import config
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb

from lib.utils import generate_token


# user model - extends webapp2 User model
class User(User):
	uid = ndb.StringProperty()
	username = ndb.StringProperty()
	email = ndb.StringProperty()
	name = ndb.StringProperty()
	timezone = ndb.StringProperty()
	country = ndb.StringProperty()
	company = ndb.StringProperty()
	blogger = ndb.BooleanProperty(default=False)
	activated = ndb.BooleanProperty(default=False)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	last_login = ndb.DateTimeProperty()
	tfsecret = ndb.StringProperty()
	tfenabled = ndb.BooleanProperty(default=False)

	@classmethod
	def get_by_email(cls, email):
		return cls.query(cls.email == email).get()

	@classmethod
	def get_by_uid(cls, uid):
		return cls.query(cls.uid == uid).get()

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.created).fetch()


# appliance group model
class Group(ndb.Model):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	owner = ndb.KeyProperty(kind=User)

	@classmethod
	def get_by_name(cls, name):
		return cls.query(cls.name == name).get()

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.created).fetch()

	@classmethod
	def get_by_owner(cls, owner):
		return cls.query(cls.owner == owner).order(-cls.created).fetch()


# class for group membership
class GroupMembers(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	group = ndb.KeyProperty(kind=Group)    
	email = ndb.StringProperty()
	member = ndb.KeyProperty(kind=User)
	invitor = ndb.KeyProperty(kind=User)
	token = ndb.StringProperty()
	active = ndb.BooleanProperty(default=False)

	@classmethod
	def invite(cls, email, group, invitor):
		# do we have this combo already?
		entry = cls.query().filter(cls.email == email, cls.group == group).get()
		
		if not entry:
			# generate new token and create new entry 
			token = "%s" % generate_token(size=16, caselimit=True)
			entry = GroupMembers(
				group = group,
				email = email,
				invitor = invitor,
				token = token,
				active = False
			)
			entry.put()

		return entry

	@classmethod
	def get_group_user_count(cls, group):
		return cls.query().filter(cls.group == group, cls.active == True).count()

	@classmethod
	def get_by_token(cls, token):
		return cls.query().filter(cls.token == token).get()

	@classmethod
	def get_by_userid_groupid(cls, user, group):
		return cls.query().filter(cls.member == user, cls.group == group).get()

	@classmethod
	def get_new_owner(cls, user, group):
		return cls.query().filter(cls.group == group, cls.member != user).get()

	@classmethod
	def get_user_groups(cls, user):
		groups = []
		entries = cls.query(cls.member == user).fetch()
		for entry in entries:
			group = Group.get_by_id(entry.group.id())
			groups.append(group)
		return groups

	@classmethod
	def get_group_users(cls, group):
		users = []
		entries = cls.query().filter(cls.group == group, cls.active == True).fetch()
		for entry in entries:
			stuff = entry.member
			user = User.get_by_id(entry.member.id())
			users.append(user)
		return users

	@classmethod
	def is_member(cls, user, group):
		entry = cls.query().filter(cls.member == user, cls.group == group).get()
		if entry:
			return True
		else:
			return False


# appliance model
class Appliance(ndb.Model):
	activated = ndb.BooleanProperty(default=True)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	token = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	group = ndb.KeyProperty(kind=Group)
	dynamicimages = ndb.BooleanProperty(default=True)
	location = ndb.GeoPtProperty()
	ipv4enabled = ndb.BooleanProperty(default=False)
	ipv6enabled = ndb.BooleanProperty(default=False)
	ipv4_address = ndb.StringProperty()

	@classmethod
	def get_by_token(cls, token):
		return cls.query(cls.token == token).get()

	@classmethod
	def get_by_user(cls, user):
		return cls.query().filter(cls.owner == user).order(-cls.created).fetch()

	@classmethod
	def get_by_group(cls, group):
		return cls.query().filter(cls.group == group).fetch()

	@classmethod
	def get_by_user_group(cls, user, group):
		return cls.query().filter(cls.owner == user, cls.group == group).fetch()

	@classmethod
	def get_appliance_count_by_user_group(cls, user, group):
		return cls.query().filter(cls.owner == user, cls.group == group).count()


# image model
class Image(ndb.Model):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	url = ndb.StringProperty()
	size = ndb.IntegerProperty()
	diskformat = ndb.StringProperty()
	containerformat = ndb.StringProperty()
	active = ndb.BooleanProperty(default=False)
	dynamic = ndb.BooleanProperty(default=False)

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(cls.created).fetch()

	@classmethod
	def get_by_name(cls, name):
		image_query = cls.query().filter(cls.name == name)
		image = image_query.get()
		return image


# flavor model
class Flavor(ndb.Model):
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	vpus = ndb.IntegerProperty()
	memory = ndb.IntegerProperty()
	disk = ndb.IntegerProperty()
	network = ndb.IntegerProperty()
	rate = ndb.IntegerProperty() # current market rate
	hot = ndb.IntegerProperty() # number hot
	launches = ndb.IntegerProperty() # number of launches
	active = ndb.BooleanProperty(default=False)

	@classmethod
	def get_all(cls):
		return cls.query().filter().order(-cls.rate).fetch()

	@classmethod
	def get_by_name(cls, name):
		flavor_query = cls.query().filter(cls.name == name)
		flavor = flavor_query.get()
		return flavor


# address model
class Address(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	address = ndb.StringProperty()


# cloud model
class Cloud(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	name = ndb.StringProperty()
	description = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	address = ndb.StringProperty()

	@classmethod
	def get_by_user(cls, user):
		cloud_query = cls.query().filter(cls.owner == user).order(-cls.created)
		clouds = cloud_query.fetch()
		return clouds

	@classmethod
	def get_by_user_name(cls, user, name):
		cloud_query = cls.query().filter(cls.owner == user, cls.name == name)
		cloud = cloud_query.get()
		return cloud


# callback model
class Callback(ndb.Model):
	name = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	json_content = ndb.StringProperty()


# wisp model
class Wisp(ndb.Model):
	name = ndb.StringProperty()
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	image = ndb.KeyProperty(kind=Image)
	ssh_key = ndb.StringProperty()
	post_creation = ndb.StringProperty()
	dynamic_image_url = ndb.StringProperty()
	callback_url = ndb.StringProperty()
	owner = ndb.KeyProperty(kind=User)
	bid = ndb.IntegerProperty()
	amount = ndb.IntegerProperty()
	default = ndb.BooleanProperty(default=False)

	@classmethod
	def get_by_user(cls, user):
		wisp_query = cls.query().filter(cls.owner == user).order(cls.name)
		wisps = wisp_query.fetch()
		return wisps

	@classmethod
	def get_by_user_name(cls, user, name):
		wisp_query = cls.query().filter(cls.owner == user, cls.name == name)
		wisp = wisp_query.get()
		return wisp

	@classmethod
	def get_user_default(cls, user):
		wisp_query = cls.query().filter(cls.owner == user, cls.default == True)
		wisp = wisp_query.get()
		return wisp

	@classmethod
	def set_default(cls, wisp):
		# find the owner of this wisp
		owner = wisp.owner
	
		# get all wisps by this owner
		wisp_query = cls.query().filter(cls.owner == owner)
		wisps = wisp_query.fetch()

		# all other wisps not default wisp
		for wispr in wisps:
			wispr.default = False
			wispr.put()

		# this wisp is default
		wisp.default = True
		wisp.put()
	
		return wisp

# instance bid model
class InstanceBid(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	cloud = ndb.KeyProperty(kind=Cloud)
	flavor = ndb.KeyProperty(kind=Flavor)
	bid = ndb.IntegerProperty()
	group = ndb.KeyProperty(kind=Group)
	wisp = ndb.KeyProperty(kind=Wisp)
	location = ndb.GeoPtProperty()
	radius = ndb.IntegerProperty()
	need_ipv4_address = ndb.BooleanProperty()
	need_ipv6_address = ndb.BooleanProperty()
	status = ndb.IntegerProperty() # 0 - not filled, 1 - filled


# instance model
class Instance(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	expires = ndb.DateTimeProperty()
	name = ndb.StringProperty()
	address = ndb.StringProperty() # bitcoin
	owner = ndb.KeyProperty(kind=User)
	appliance = ndb.KeyProperty(kind=Appliance)
	cloud = ndb.KeyProperty(kind=Cloud)
	flavor = ndb.KeyProperty(kind=Flavor)
	ask = ndb.IntegerProperty()
	wisp = ndb.KeyProperty(kind=Wisp)
	ipv4_private_address = ndb.StringProperty()
	ipv4_address = ndb.StringProperty()
	ipv6_address = ndb.StringProperty()
	state = ndb.IntegerProperty()

	@classmethod
	def get_by_name_appliance(cls, name, appliance):
		instance_query = cls.query().filter(cls.name == name, cls.appliance == appliance)
		instance = instance_query.get()
		return instance

	@classmethod
	def get_by_name(cls, name):
		instance_query = cls.query().filter(cls.name == name)
		instance = instance_query.get()
		return instance

	@classmethod
	def get_by_appliance(cls, appliance):
		instance_query = cls.query().filter(cls.appliance == appliance)
		instances = instance_query.fetch()
		return instances

	# insert or update instance
	# note that appliance is an object, not a key
	@classmethod
	def push(cls, appliance_instance, appliance):
		# check if we have it
		instance = cls.query().filter(cls.name == appliance_instance['name']).get()

		if not instance:
			# lookup image and flavor info
			image = Image().get_by_name(appliance_instance['image'])
			flavor = Flavor().get_by_name(appliance_instance['flavor'])
			
			# create new entry
			instance = Instance()
			instance.name = appliance_instance['name']
			instance.address = appliance_instance['address']
			instance.ask = appliance_instance['ask']
			instance.state = appliance_instance['state']
			instance.expires = datetime.fromtimestamp(long(appliance_instance['expires']))
			instance.flavor = flavor.key
			instance.image = image.key
			instance.appliance = appliance.key
			instance.owner = appliance.owner
			instance.put()
		else:
			# update ask
			instance.ask = appliance_instance['ask']
			instance.put()

		return instance
		
	@classmethod
	def update(cls, appliance_instance, appliance):
		pass

# blog posts and pages
class Article(ndb.Model):
	created = ndb.DateTimeProperty(auto_now_add=True)
	updated = ndb.DateTimeProperty(auto_now=True)
	owner = ndb.KeyProperty(kind=User)
	title = ndb.StringProperty()
	summary = ndb.StringProperty()
	filename = ndb.StringProperty()
	slug = ndb.StringProperty()
	article_type = ndb.StringProperty()
	draft = ndb.BooleanProperty(default=True)
	
	@classmethod
	def get_all(cls):
		article_query = cls.query().filter().order(-cls.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_blog_posts(cls, num_articles=1, offset=0):
		article_query = cls.query().filter(cls.article_type == 'post', cls.draft == False).order(-cls.created)
		articles = article_query.fetch(limit=num_articles)
		return articles

	@classmethod
	def get_by_user(cls, user):
		article_query = cls.query().filter(cls.owner == user).order(-Article.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_by_type(cls, article_type):
		article_query = cls.query().filter(cls.article_type == article_type).order(-Article.created)
		articles = article_query.fetch()
		return articles

	@classmethod
	def get_by_slug(cls, slug):
		article_query = cls.query().filter(cls.slug == slug)
		article = article_query.get()
		return article


# log tracking pings
class LogTracking(ndb.Model):
	timestamp = ndb.DateTimeProperty(auto_now_add=True)
	message = ndb.StringProperty()
	ip = ndb.StringProperty()    


# log visits
class LogVisit(ndb.Model):
	timestamp = ndb.DateTimeProperty(auto_now_add=True)
	user = ndb.KeyProperty(kind=User)
	message = ndb.StringProperty()
	uastring = ndb.StringProperty()
	ip = ndb.StringProperty()


# log outgoing emails
class LogEmail(ndb.Model):
	sender = ndb.StringProperty(
		required=True)
	to = ndb.StringProperty(
		required=True)
	subject = ndb.StringProperty(
		required=True)
	body = ndb.TextProperty()
	when = ndb.DateTimeProperty()

