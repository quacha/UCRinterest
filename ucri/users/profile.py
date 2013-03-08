import os, subprocess
from bcrypt import hashpw, gensalt
from flask import Flask, request, render_template, redirect, url_for, flash, current_app, Blueprint
from flask.ext.login import current_user, login_required, confirm_login, fresh_login_required, logout_user
from werkzeug import secure_filename
from datetime import datetime
from forms import RegisterForm, SettingsForm, PasswordForm, InterestForm
from ucri import DEFAULT_PROFILE_PIC, DEFAULT_PROFILE_PIC_PATH, DEFAULT_PROFILE_PIC_LOC
from ucri.models.user import User
from ucri.data.forms import UploadForm
from ucri.data.pin import allowed_file, addInvalidBrowser, rmInvalidBrowser, addInvalidCommenter, rmInvalidCommenter

# Profile blueprint
mod = Blueprint('profile', __name__)

def updateAllPermissions(new_usr):
    '''
    Updates the permissions of all other users 
    to handle the case where a user has 
    selected nobody to see their pins or 
    comment on their pins
    '''
    invalidate_choices = ['R', 'L', 'B', 'N']
    for usr in User.objects.all():
        if usr.pin_browsers in invalidate_choices:
            addInvalidBrowser(usr, new_usr)

        if usr.pin_commenters in invalidate_choices:
            addInvalidCommenter(usr, new_usr)

def createNewUser(form):
    hashedpwd = hashpw(form.pwd.data, gensalt(log_rounds=13))
    usr = User(uname=form.uname.data,
               fname=form.fname.data,
               lname=form.lname.data,
               img=DEFAULT_PROFILE_PIC,
               email=form.email.data,
               gender=form.gender.data,
               pin_browsers='E',
               pin_commenters='E',
               pwd=hashedpwd,
               dscrp=form.dscrp.data,
               bday=form.bday.data,
               creation_date=datetime.now())
    usr.save()
    # Put this user in the permissions of other users
    updateAllPermissions(usr)
    flash('Thanks for registering!')
    return redirect(url_for('login.login'))

@mod.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        try:
            usrQuery = User.objects.get(uname=form.data['uname'])
            if usrQuery is not None:
                flash('Username already exists!')
                redirect(url_for('profile.register'))
            else:
                return createNewUser(form)
        except User.DoesNotExist:
            return createNewUser(form)
    return render_template('register.html', form=form)

########## Settings ##########
@login_required
def changeProfilePic(form):
    filename = form.img.file.filename
    if form.validate() and filename != DEFAULT_PROFILE_PIC and allowed_file(filename):
        # Remove old_profile pic from storage
        if current_user.img != DEFAULT_PROFILE_PIC:
            subprocess.call("rm -f photos/%s" % str(current_user.img), shell=True)
        # Store file
        filename = current_user.uname + '_' + secure_filename(form.img.data.filename)
        # Save to DB
        form.img.file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        current_user.update(set__img=filename)
        current_user.save()
        # Successfully change pic
        flash("Successfully changed profile picture to %s" % filename)
        return render_template("settings.html", form=form, upform=UploadForm())
    return render_template("settings.html", form=form, upform=UploadForm())

@login_required
def getFollowerPermissions():
    return User.objects.filter(follower_array__not__contains=current_user.to_dbref())

@login_required
def getFollowingPermissions():
    invalid = []
    usrs = User.objects.all()
    for usr in usrs:
        if usr.to_dbref() not in current_usr.follower_array:
            invalid.append(usr.to_dbref())
    return invalid

@login_required
def updateUserBrowserPermissions(form):
    '''
    Updates browser permissions on users pins
    '''
    perm = form.data['pin_browsers']
    current_user.update(set__pin_browsers=perm)
    # Everyone has permission
    if perm == 'E':
        current_user.invalid_browsers = []
    # Your followers have permission
    elif perm == 'R':
        current_user.invalid_browsers = getFollowerPermissions()
    # People you follow have permission
    elif perm == 'L':
        current_user.invalid_browsers = getFollowingPermissions()
    # Followers and following get permission
    elif perm == 'B':
        current_user.invalid_browsers = getFollowerPermissions().extend(getFollowingPermissions())
    elif perm == 'N':
        current_user.invalid_browsers = User.objects.all()
    return perm == 'C'

@login_required
def updateUserCommenterPermissions(form):
    '''
    Updates commenter permissions on users pins
    '''
    perm = form.data['pin_commenters']
    current_user.update(set__pin_commenters=perm)
    # Everyone has permission
    if perm == 'E':
        current_user.invalid_commenters = []
    # Your followers have permission
    elif perm == 'R':
        current_user.invalid_commenters = getFollowerPermissions()
    # People you follow have permission
    elif perm == 'L':
        current_user.invalid_commenters = getFollowingPermissions()
    # Followers and following get permission
    elif perm == 'B':
        current_user.invalid_commenters = getFollowerPermissions().extend(getFollowingPermissions())
    elif perm == 'N':
        current_user.invalid_commenters = User.objects.all()
    return perm == 'C'

@login_required
def updateSettings(form):
    if form.validate():
        # Set all string fields
        current_user.update(set__fname=form.data['fname'])
        current_user.update(set__lname=form.data['lname'])
        current_user.update(set__email=form.data['email'])
        current_user.update(set__gender=form.data['gender'])
        current_user.update(set__bday=form.data['bday'])
        current_user.update(set__dscrp=form.data['dscrp'])
        # Update permissions
        custom_browse, custom_comment = False, False
        if current_user.pin_browsers != form.data['pin_browsers']:
            custom_browse = updateUserBrowserPermissions(form)
        if current_user.pin_commenters != form.data['pin_commenters']:
            custom_comment = updateUserCommenterPermissions(form)
        current_user.save()
        flash("Settings have been saved successfully!")
        # Go to profile
        if not custom_browse and not custom_comment:
            return redirect("/viewprofile/pins")
        else:
            flash("Custom")
            return redirect(url_for("index"))
    flash("Form is invalid!")
    return render_template("settings.html", form=form, upform=UploadForm())

@mod.route('/deactivate')
@login_required
def deactivateAccount():
    # Delete profile picture
    if current_user.img != DEFAULT_PROFILE_PIC:
        subprocess.call("rm -f photos/%s" % str(current_user.img), shell=True)
    # Delete user from database
    current_user.delete()
    logout_user()
    flash("Account has been deactivated!")
    return redirect(url_for('index'))

@mod.route('/settings', methods=['GET', 'POST'])
@login_required
def profileSettings():
    form = SettingsForm(obj=current_user)
    if request.method == 'POST':
        # Handle deactivation
        if form.data['deactivate']:
            return redirect(url_for('profile.deactivateAccount'))
        # Handle changing password
        if form.data['change_pwd']:
            return redirect(url_for('profile.setPassword'))
        # Handle changing profile pic
        if len(form.img.file.filename) > 0 and form.img.file.filename != DEFAULT_PROFILE_PIC  and form.img.file.filename != current_user.img.strip(current_user.uname + '_'):
            return changeProfilePic(form)
        # Update the other user settings
        return updateSettings(form)
    return render_template("settings.html", form=form, upform=UploadForm())

@mod.route('/settings/pwd', methods=['GET', 'POST'])
@login_required
def setPassword():
    form = PasswordForm(request.form)
    if request.method == "POST" and form.validate():
        hashedpwd = hashpw(form.pwd.data, gensalt(log_rounds=13))
        current_user.update(set__pwd=hashedpwd)
        current_user.save()
        flash("Password was changed successfully")
        return redirect('/settings')
    return render_template("newpassword.html", form=form, upform=UploadForm())

##############################

@mod.route('/interests', methods=['GET', 'POST'])
def addInterests():
    form = InterestForm(request.form)
    if request.method == 'POST' and form.validate():     
        pass

@mod.route('/follow', methods=["POST"])
def follow():
    id = request.form.get('pinner')
    user = User.objects.get(id=id)
    current_user.follower_array.append(user)
    current_user.save()
    flash("Following " + user.uname)
    return redirect("/viewprofile/following")

@mod.route('/clearfollows')
def clearfollows():
    users = User.objects
    for user in users:
        user.follower_array = None
        user.save()
    flash("Follows cleared")
    return redirect('/index')
