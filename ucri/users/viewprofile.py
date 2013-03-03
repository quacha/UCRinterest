from flask import (Flask, request, render_template, redirect, url_for, flash,
                   current_app, Blueprint)
from flask.ext.login import (current_user, login_required, confirm_login,
                             fresh_login_required)
from datetime import datetime
from ucri.models.user import User
#from ucri.models.board import Board
from ucri.models.pin import Pin
from ucri.data.forms import UploadForm

mod = Blueprint('viewprofile', __name__)

@mod.route('/viewprofile')
@login_required
def viewprofile():
	return render_template('viewprofile.html', upform=UploadForm())

@mod.route('/viewprofile/pins')
@login_required
def profilepins():
	pins = Pin.objects(pinner=current_user.to_dbref()).order_by('-date')
	return render_template('profilepins.html', pins=pins, upform=UploadForm())

@mod.route('/viewprofile/likes')
@login_required
def likedpins():
	pins = Pin.objects(likes__contains=current_user.to_dbref())
	return render_template('profilepins.html', pins=pins, upform=UploadForm())

@mod.route('/viewprofile/favorites')
@login_required
def favorites():
	pins = Pin.objects(favs__contains=current_user.to_dbref())
	return render_template('profilepins.html', pins=pins, upform=UploadForm())

@mod.route('/viewprofile/following')
@login_required
def following():
	users = current_user.follower_array
	return render_template('profilefollows.html', users=users, upform=UploadForm())

@mod.route('/viewprofile/followers')
@login_required
def followers():
	users = User.objects.filter(follower_array__contains=current_user.to_dbref())
	return render_template('profilefollows.html', users=users, upform=UploadForm())
