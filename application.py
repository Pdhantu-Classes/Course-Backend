import json
import os
from datetime import datetime
import time
import calendar
import hashlib
from flask import request
from flask import Flask
import math
import jwt
import boto3
from botocore.client import Config
from flask_cors import CORS
from flask_mysqldb import MySQL
import razorpay
import string
import random
import hmac
import hashlib


# S3 buket Credential
ACCESS_KEY_ID = 'AKIAIVI7KFEM5MDNWJAQ'
ACCESS_SECRET_KEY = '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'
BUCKET_NAME = 'pdhantu-classes'

# Test Razor Pay Credential
# RAZORPAY_KEY = 'rzp_test_x8I5D7s72Z0kOk'
# RAZORPAY_SECRET = 'IsPwjbGZx9vojbrA95vVoXzd'

# Live  Razor Pay Credential
RAZORPAY_KEY = 'rzp_live_dG54e74x2QdKcw'
RAZORPAY_SECRET = 'YqklWxoyHIc1s9boGOL94Z4B'


# Database Credential Development
MYSQL_HOST = 'database-pdhantu.cqa6f6gkxqbj.us-east-2.rds.amazonaws.com'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'root_123'
# MYSQL_DB = 'pdhantu-dev'
MYSQL_DB = 'pdhantu-prod'
MYSQL_CURSORCLASS = 'DictCursor'


app = Flask(__name__)
CORS(app)

# Database Connection
app.config['MYSQL_HOST'] = MYSQL_HOST
app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
app.config['MYSQL_CURSORCLASS'] = MYSQL_CURSORCLASS
mysql = MySQL(app)


razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))


def hmac_sha256(val):
    h = hmac.new(RAZORPAY_SECRET.encode("ASCII"), val.encode(
        "ASCII"), digestmod=hashlib.sha256).hexdigest()
    print(h)
    return h

# Upload Photo to S3 bucket
def uploadFileToS3(fileName, file):
    s3 = boto3.resource(
        's3',
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=ACCESS_SECRET_KEY,
        config=Config(signature_version='s3v4')
    )
    s3.Bucket(BUCKET_NAME).put_object(Key=fileName, Body=file)

# Generate MD5 hashing
def md5_hash(string):
    hash = hashlib.md5()
    hash.update(string.encode('utf-8'))
    return hash.hexdigest()

# Generate Salt
def generate_salt():
    salt = os.urandom(16)
    return salt.hex()

# Generate Random String
def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


# Test
@app.route('/course', methods=["GET"])
def hello():
    return "Hello World"

# SignUp
@app.route('/course/signup', methods=['POST'])
def signUp():
    firstname = request.json['firstname']
    lastname = request.json['lastname']
    email = request.json['email']
    password = request.json['password']
    mobile = request.json['mobile']
    created_at = datetime.fromtimestamp(calendar.timegm(time.gmtime()))
    flag = False
    password_salt = generate_salt()
    password_hash = md5_hash(password + password_salt)
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT * FROM course_users where email = (%s)""", [email])
    results = cursor.fetchone()
    if results:
        flag = True
        mysql.connection.commit()
        cursor.close()
    if flag == True:
        response = app.response_class(response=json.dumps(
            {"message": "Already Exist", "isValid": False}), status=200, mimetype='application/json')
        return response
    else:
        cursor.execute(
            """INSERT INTO course_users (firstname, lastname, email, mobile, password_hash, password_salt, sign_up_method, is_active, role, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) """, (
                firstname, lastname, email, mobile, password_hash, password_salt, "NORMAL", True, "USER", created_at)
        )
        mysql.connection.commit()
        cursor.close()
        response = app.response_class(response=json.dumps(
            {"message": "Sign Up Successfully", "isValid": True}), status=200, mimetype='application/json')
        return response

# User Login
@app.route('/course/login', methods=["POST"])
def userLogin():
    email = request.json["email"]
    password = request.json["password"]
    isUserExist = False
    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT * FROM course_users where email=(%s)""", [email])
    user_data = cursor.fetchone()
    response = {}
    if user_data:
        if str(user_data["password_hash"]) == str(md5_hash(password+user_data["password_salt"])):
            isUserExist = True

        if isUserExist:
            print(user_data)
            encoded_jwt = jwt.encode({"user_id": user_data["id"], "firstname": user_data["firstname"],"lastname":user_data["lastname"],"mobile":user_data["mobile"],
                                      "email": user_data["email"], "role": user_data["role"],"module": user_data["module"]}, 'secretkey', algorithm='HS256').decode("utf-8")
            response = app.response_class(response=json.dumps(
                {"message": "Login Success", "isValid": True, "token": encoded_jwt, "image_url": user_data["image_url"]}), status=200, mimetype='application/json')
            return response
        else:
            response = app.response_class(response=json.dumps(
                {"message": "Wrong Credential", "isValid": False}), status=200, mimetype='application/json')
            return response
    else:
        response =app.response_class(response=json.dumps({"message":"User do not exists, Please sign up"}),status= 200, mimetype='application/json')
        return response


# User Forget Password
@app.route('/course/forgetPassword', methods=["POST"])
def forgetPassword():
    email = request.json["email"]
    mobile = request.json["mobile"]
    isUserExist = False
    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT * FROM course_users where email=(%s) AND mobile=(%s)""", [email, mobile])
    user_data = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    print(user_data)
    if user_data:
        isUserExist = True
    if isUserExist:
        response = app.response_class(response=json.dumps({"message": "Please Enter New Password", "isValid": True, "user_id": user_data["id"]}), status=200, mimetype='application/json')
        return response
    else:
        response = app.response_class(response=json.dumps({"message": "Please Enter Valid Details", "isValid": False}), status=200, mimetype='application/json')
        return response

# User Change Password
@app.route('/course/changePassword', methods=["PUT"])
def changePassword():
    user_id = request.json["user_id"]
    password = request.json["password"]
    password_salt = generate_salt()
    password_hash = md5_hash(password + password_salt)
    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE course_users SET password_hash = (%s), password_salt = (%s) where id = (%s)""", [password_hash,password_salt,user_id])
    mysql.connection.commit()
    cursor.close()
    response = app.response_class(response=json.dumps({"message": "Password Change Successfully", "isValid": True}), status=200, mimetype='application/json')
    return response


# Razorpay Create Order
@app.route('/course/createOrder', methods=['POST'])
def createOrder():
    package_id = request.json["package_id"]
    user_id = request.json["user_id"]
    initiate_at = datetime.fromtimestamp(calendar.timegm(time.gmtime()))
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT package_price FROM course_package where id=(%s)""", [package_id])
    result = cursor.fetchone()
    paye_id = randomString(10)
    order_amount = int(result["package_price"]) * 100
    order_currency = 'INR'
    order_receipt = 'order_'+paye_id
    cursor.execute("""INSERT into course_order_initiates(order_id, user_id, package_id, price, initiate_at) values(%s,%s,%s,%s,%s)""", [order_receipt, user_id ,package_id, order_amount/100, initiate_at])
    razorId = razorpay_client.order.create(
        amount=order_amount, currency=order_currency, receipt=order_receipt, payment_capture='1')
    mysql.connection.commit()
    cursor.close()
    return json.dumps(razorId["id"])


# Razorpay Verify Signature
@app.route('/course/verifyRazorpaySucces', methods=['POST'])
def verifyPayment():
    user_id = request.json["user_id"]
    package_id=request.json["package_id"]
    request_order_id = request.json["order_id"]
    request_payment_id = request.json["payment_id"]
    request_signature = request.json["signature"]
    is_success = False
    order_at = datetime.fromtimestamp(calendar.timegm(time.gmtime()))
    generated_signature = hmac_sha256(request_order_id+ "|" + request_payment_id)
    status='failure'
    if(generated_signature == request_signature):
        is_success=True
        status='success'
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT package_price FROM course_package where id=(%s)""", [package_id])
    result = cursor.fetchone()
    cursor.execute("""UPDATE course_order_initiates SET status = (%s) where user_id =(%s) and package_id=(%s)""",[status,user_id,package_id])
    cursor.execute("""INSERT into course_order_history(payment_id,order_id,user_id,price,order_at,status,package_id) values(%s,%s,%s,%s,%s,%s,%s)""", [request_payment_id,request_order_id,user_id,result["package_price"],order_at,status,package_id])
    mysql.connection.commit()
    cursor.close()
    return json.dumps({"isSuccess": is_success})


# Check User Registered
@app.route('/course/isUserRegister/<int:user_id>', methods=["GET"])
def isUserRegister(user_id):
    cursor = mysql.connection.cursor()
    isValid = False
    cursor.execute("""SELECT course FROM course_users where id=(%s)""", [user_id])
    result = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    if result["course"]:
        isValid = True
    response =app.response_class(response=json.dumps({"message":"User details exist", "isValid":isValid, "package_id":result["course"]}),status= 200, mimetype='application/json')
    return response

# Get Profile Details
@app.route('/userDetails/<int:user_id>', methods=["GET"])
def getUserDetails(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT cu.*, cp.package_name as courses  FROM course_users cu left join course_package cp on cu.course = cp.id where cu.id=(%s)""", [user_id])
    result = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"User details exist","user_data":result}),status= 200, mimetype='application/json')
    return response


# Upload Profile Image
@app.route('/course/upload-image', methods=["POST"])
def uploadImage():
    isUpload = False
    response = {}
    file = request.files["file"]
    seconds = str(time.time()).replace(".","")
    newFile = "user-images/"+seconds + "-" + file.filename
    uploadFileToS3(newFile, file)
    image_url = 'https://pdhantu-classes.s3.us-east-2.amazonaws.com/'+newFile
    isUpload = True
    response["isUpload"] = isUpload
    response["imageUrl"] = image_url
    return json.dumps(response)

# Change Profile Details 
@app.route('/course/userDetails/<int:user_id>', methods=["PUT"])
def postUserDetails(user_id):
    whatsapp = request.json["whatsapp"]
    graduation_year = request.json["graduation_year"]
    course = request.json["course"]
    gender = request.json["gender"]
    dob = request.json["dob"]
    address = request.json["address"]
    pincode = request.json["pincode"]
    qualification = request.json["qualification"]
    occupation = request.json["occupation"]
    fathers_name = request.json["fathers_name"]
    medium = request.json["medium"]
    imageUrl = request.json["imageUrl"]
    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE course_users SET whatsapp =(%s), graduation_year=(%s), course=(%s), gender=(%s), dob=(%s), address=(%s), pincode=(%s), qualification=(%s), occupation=(%s), fathers_name=(%s), medium=(%s), image_url =(%s)  where id=(%s)""", [whatsapp, graduation_year, course, gender, dob, address, pincode, qualification, occupation, fathers_name, medium,imageUrl, user_id])
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"User Data Added Successfully"}),status= 200, mimetype='application/json')
    return response


# Get All Test Series bought by User
@app.route('/course/myOrders/<int:user_id>',methods=["GET"])
def myOrders(user_id):
    isValid = False
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT coh.*, cp.package_name FROM course_order_history coh left join course_package cp on coh.package_id= cp.id where coh.user_id =(%s) AND coh.status ="success" limit 1""", [user_id])
    result = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    if result:
        isValid = True
    response =app.response_class(response=json.dumps({"isValid":isValid,"orders":result}),status= 200, mimetype='application/json')
    return response

# Check Package Buy or NOT
@app.route('/course/isPackageBuy/<int:user_id>',methods=["GET"])
def checkOrderDetails(user_id):
    isValid = False
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT id FROM course_order_history where user_id =(%s) AND status ="success" limit 1""", [user_id])
    result = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    if result:
        isValid = True
    response =app.response_class(response=json.dumps({"isValid":isValid}),status= 200, mimetype='application/json')
    return response

##### Admin End #####

# Admin Login
@app.route('/course/adminLogin', methods=["POST"])
def adminLogin():
    username = request.json["username"]
    password = request.json["password"]
    isAdminExist = False
    cursor = mysql.connection.cursor()
    cursor.execute(
        """SELECT * FROM admin_table where username=(%s) AND password=(%s)""", [username, password])
    admin_data = cursor.fetchone()
    if admin_data:
        isAdminExist = True
    if isAdminExist:
        response = app.response_class(response=json.dumps({"message": "Login Success", "isValid": True, "admin": admin_data}), status=200, mimetype='application/json')
        return response
    else:
        response = app.response_class(response=json.dumps({"message": "Wrong Credential", "isValid": False}), status=200, mimetype='application/json')
        return response

#Admin Dashboard
@app.route('/course/adminDashboard',methods=["GET"])
def adminDashboard():
    cursor = mysql.connection.cursor()
    cursor.execute(""" select count(*) as total from course_users""")
    total = cursor.fetchone()
    cursor.execute(""" select count(*) as total from course_users u join course_order_history o on u.id = o.user_id""")
    paid = cursor.fetchone()
    cursor.execute(""" select count(*) as total from course_users where course = 1""")
    prelims = cursor.fetchone()
    cursor.execute(""" select count(*) as total from course_users where course = 2""")
    mains = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Users data are:", "total_user":total["total"], "paid_user": paid['total'], "prelims":prelims["total"], "mains":mains["total"] }),status= 200, mimetype='application/json')
    return response

#All Users
@app.route('/course/allUsers',methods=["GET"])
def getAllUsers():
    page = request.headers.get("page")
    offset = 20*(int(page)-1)
    cursor = mysql.connection.cursor()
    cursor.execute(""" select * from course_users order by id desc limit 20 offset %s """,[offset])
    result = cursor.fetchall()
    cursor.execute(""" select count(*) as total from users""")
    total = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Users data are", "user_data":result, "total": total['total']}),status= 200, mimetype='application/json')
    return response


#Paid Users
@app.route('/course/paidUsers',methods=["GET"])
def getPaidUsers():
    page = request.headers.get("page")
    offset = 20*(int(page)-1)
    cursor = mysql.connection.cursor()
    cursor.execute(""" select u.*, o.* from course_users u join course_order_history o on u.id = o.user_id order by u.id desc limit 20 offset %s""", [offset])
    result = cursor.fetchall()
    cursor.execute(""" select count(*) as total from course_users u join course_order_history o on u.id = o.user_id""")
    total = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Users data are", "user_data":result, "total": total['total']}),status= 200, mimetype='application/json')
    return response

#Unpaid Users
@app.route('/course/unpaidUsers',methods=["GET"])
def getUnpaidUsers():
    page = request.headers.get("page")
    offset = 20*(int(page)-1)
    cursor = mysql.connection.cursor()
    cursor.execute(""" select course_users.* from course_users left outer join course_order_history on course_users.id = course_order_history.user_id where course_order_history.user_id is null order by course_users.id desc limit 20 offset %s""", [offset])
    result = cursor.fetchall()
    cursor.execute(""" select count(*) as total from course_users left outer join course_order_history on course_users.id = course_order_history.user_id where course_order_history.user_id is null""")
    total = cursor.fetchone()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Users data are", "user_data":result, "total": total['total']}),status= 200, mimetype='application/json')
    return response

#Disputed Users
@app.route('/course/disputeOrders',methods=["GET"])
def disputeOrders():
    cursor = mysql.connection.cursor()
    cursor.execute(""" select cu.firstname, cu.lastname, cu.email, coi.user_id, coi.id, coi.order_id, coi.package_id, coi.price, coi.initiate_at from course_order_initiates coi left join course_users cu on coi.user_id = cu.id where status is null order by coi.id desc""")
    result = cursor.fetchall()
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Users data are", "order_data":result}),status= 200, mimetype='application/json')
    return response

# Resolve Orders
@app.route('/course/resolveOrder',methods=["POST"])
def resolveOrder():
    payment_id = request.json["payment_id"]
    initiate_id = request.json["initiate_id"]
    cursor = mysql.connection.cursor()
    cursor.execute(""" select * from course_order_initiates where id =(%s)""",[initiate_id])
    result = cursor.fetchone()
    cursor.execute(""" update course_order_initiates set status='success' where id =(%s)""",[initiate_id])
    cursor.execute(""" insert into course_order_history(payment_id, order_id, user_id, price, order_at, package_id, status) values(%s,%s,%s,%s,%s,%s,%s)""",[payment_id,result["order_id"],result["user_id"],result["price"],result["initiate_at"],result["package_id"],"success"])
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Successfully Resolved", "isValid":True}),status= 200, mimetype='application/json')
    return response

# Delete Orders
@app.route('/course/deleteDisputeOrder',methods=["DELETE"])
def deleteDisputeOrder():
    initiate_id = request.json["initiate_id"]
    cursor = mysql.connection.cursor()
    cursor.execute(""" delete from course_order_initiates where id =(%s)""",[initiate_id])
    mysql.connection.commit()
    cursor.close()
    response =app.response_class(response=json.dumps({"message":"Successfully Deleted", "isValid":True}),status= 200, mimetype='application/json')
    return response

if __name__ == "__main__":
    app.run(debug="True", host="0.0.0.0", port=5001)
    # app.run(debug = "True")
