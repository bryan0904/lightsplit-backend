from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# 暂存房间资料（后面可以接数据库）
rooms = {}

# 根路由，欢迎信息
@app.route('/')
def home():
    return "Welcome to the lightsplit app!"

# 创建房间
@app.route('/create_room', methods=['POST'])
def create_room():
    data = request.json
    room_id = str(uuid.uuid4())  # 生成一个唯一的房间ID
    rooms[room_id] = {
        "title": data.get("title"),  # 房间的标题
        "members": data.get("members"),  # 房间成员
        "payments": {}  # 存储每个成员的支付信息
    }
    return jsonify({"room_id": room_id})

# 提交付款
@app.route('/submit_payment/<room_id>', methods=['POST'])
def submit_payment(room_id):
    data = request.json
    name = data.get("name")  # 成员姓名
    amount = data.get("amount")  # 付款金额
    # 查找房间并存储付款信息
    if room_id in rooms:
        rooms[room_id]["payments"][name] = amount
        return jsonify({"message": "Payment saved!"})
    return jsonify({"error": "Room not found"}), 404

# 获取结算结果
@app.route('/result/<room_id>', methods=['GET'])
def get_result(room_id):
    if room_id not in rooms:
        return jsonify({"error": "Room not found"}), 404
    
    room = rooms[room_id]
    payments = room["payments"]
    members = room["members"]
    
    # 确保所有成员都有支付数据，如果没有则设为0
    for member in members:
        if member not in payments:
            payments[member] = 0
    
    total = sum(value if value is not None else 0 for value in payments.values())
    avg = total / len(members)  # 计算每个人应该支付的平均金额
    
    # 计算每个人的余额
    balances = {name: round(amount - avg, 2) for name, amount in payments.items()}
    
    # 计算具体的转账指令
    transactions = []
    # 复制一份余额表进行操作
    balances_copy = balances.copy()
    
    # 持续结算直到所有人的余额接近0
    while any(abs(balance) > 0.01 for balance in balances_copy.values()):
        # 找到最大的债权人和债务人
        max_creditor = max(balances_copy.items(), key=lambda x: x[1] if x[1] > 0 else -float('inf'))
        max_debtor = min(balances_copy.items(), key=lambda x: x[1] if x[1] < 0 else float('inf'))
        
        # 如果没有债权人或债务人，退出循环
        if max_creditor[1] <= 0 or max_debtor[1] >= 0:
            break
        
        # 计算转账金额
        amount = min(max_creditor[1], -max_debtor[1])
        amount = round(amount, 2)  # 四舍五入到两位小数
        
        # 更新余额
        balances_copy[max_creditor[0]] -= amount
        balances_copy[max_debtor[0]] += amount
        
        # 添加交易记录
        transactions.append({
            "from": max_debtor[0],
            "to": max_creditor[0],
            "amount": amount
        })
    
    return jsonify({
        "room_id": room_id,
        "title": room["title"],
        "balances": balances,
        "transactions": transactions,
        "total_spent": total,
        "average_per_person": round(avg, 2)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001, use_reloader=False)
    

