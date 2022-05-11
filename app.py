from flask import Flask, render_template, request, jsonify, redirect, url_for
from pymongo import MongoClient  # pymongo를 임포트 하기
import datetime
import hashlib
import jwt
from bson.objectid import ObjectId

SECRET_KEY = 'Eban5joDangStar'

client = MongoClient(
    'mongodb+srv://duck:1234@cluster0.8lepp.mongodb.net/Cluster0?retryWrites=true&w=majority')  # Atlas에서 가져올 접속 정보
db = client.dogstagram

app = Flask(__name__)


# 메인화면
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('index.html', isOn="on")
    except jwt.ExpiredSignatureError:
        return render_template('index.html', isOn="off")
    except jwt.exceptions.DecodeError:
        return render_template('index.html', isOn="off")


# 자랑하기
@app.route('/addboard')
def addboard():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('addboard.html')
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        # 로그인 후 원래 페이지로 돌아가기 위해 redirectUrl을 뿌려줌
        # 아래처럼 리다이렉트하면 브라우저 url이 /login?redirectUrl=addboard처럼 변경되고 login()
        # 함수가 호출되어 render_template('login.html') 로 login.html 화면이 나타난다.
        # 로그인 페이지를 렌더하는 login()함수에서 redirectUrl 쿼리 파라미터를 받아 사용하지 않고
        # 클라이언트에서 브라우저의 url을 파싱해서 로그인 요청이 완료되면 해당 페이지로 이동시킴!
        return redirect(url_for("login", redirectUrl="addboard"))


# 로그인
@app.route('/login')
def login():

    return render_template('login.html')


# 게시글 올리기 API
@app.route('/api/addboard', methods=['POST'])
def posting():
    title_receive = request.form["title_give"]
    comment_receive = request.form["comment_give"]
    file = request.files["file_give"]
    # static 폴더에 저장될 파일 이름 생성하기
    today = datetime.datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    filename = f'file-{mytime}'
    # 확장자 나누기
    extension = file.filename.split('.')[-1]
    # static 폴더에 저장
    save_to = f'static/boardImage/{filename}.{extension}'
    file.save(save_to)

    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userID = payload['id']
    except jwt.ExpiredSignatureError:
        return redirect(url_for("", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("", msg="로그인 시간이 만료되었습니다."))

    # DB에 저장
    doc = {
        'title': title_receive,
        'userID': userID,
        'comment': comment_receive,
        'file': f'{filename}.{extension}',
        'good': []
    }
    db.board.insert_one(doc)

    return jsonify({'msg': '업로드 완료!'})


###### 로그인과 회원가입을 위한 API #####

## 아이디 중복확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    userid_receive = request.form['userid_give']
    exists = bool(db.user.find_one({"id": userid_receive}))
    ## 변수명이 잘못되어 테스트함
    # print(f'유저아이디 : {userid_receive}, bool: {exists}')
    return jsonify({'result': 'success', 'exists': exists})


## 회원가입 API
@app.route('/api/register', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']
    ## 해쉬를 이용해 pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive})

    return jsonify({'result': 'success'})


## 로그인 API
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    ## 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=300)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        ## token과 redirectURL을 -> 클라이언트에서 로그인 후 이 정보로 리다이이렉트
        return jsonify({'result': 'success', 'token': token})
    ## 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# 보안: 로그인한 사용자만 통과할 수 있는 API
@app.route('/api/isAuth', methods=['GET'])
def api_valid():
    token_receive = request.cookies.get('mytoken')
    try:
        # token을 시크릿키로 디코딩합니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'nickname': userinfo['nick']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        # 로그인 정보가 없으면 에러가 납니다!
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})



#게시글 목록 가져오기
@app.route("/get_contents", methods=['GET'])
def get_contents():
    boards = list(db.board.find().limit(20))
    return render_template('content_list.html', boards=boards)


#게시글 한건 보기 조회
@app.route("/get_content_one", methods=['GET'])
def get_content_one():
    token_receive = request.cookies.get('mytoken')
    # token을 시크릿키로 디코딩합니다.
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
    user = payload['id']
    userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})

    boardID = request.args.get("boardID")

    post = list(db.board.find({'_id':ObjectId(boardID)}))
    comments = list(db.comment.find({'_id':ObjectId(boardID)}))
    if len(comments) == 0:
        return render_template('content.html', post=post)
    return render_template('content.html', post=post, comments=comments,user=user)

#댓글 추가
@app.route('/add_comment', methods=['POST'])
def add_comment():
    content_id = request.args.get("boardID")
    comment = request.args.get("comment")
    userID  = 'test1'
    doc = {
        "content_id": content_id,
        "userID": userID ,
        "comment": comment,
    }
    db.comment.insert_one(doc)
    comment = list(db.comment.find({'_id':ObjectId(content_id)}))
    print(comment)
    return  render_template('content.html', comment=comment)

@app.route('/delete_comment', methods=['GET'])
def delete_comment():
     boardID = request.args.get("boardID")
     commentID = request.args.get("commentID")
     token_receive = request.cookies.get('mytoken')
     payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
     loginuserID = payload['id']
     comment =list(db.comment.find({'_id':ObjectId(commentID),'userID': loginuserID}))
     doc = {
         "boardID": boardID,
         "userID ": loginuserID,
         "_id ": commentID
     }
     if comment is not None:
         db.comment.delete_one(doc)
         return jsonify({'result': 'success'})
         ## 찾지 못하면
     else:
         return jsonify({'result': 'fail', 'msg': '해당 댓글작성자가 아닙니다.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
