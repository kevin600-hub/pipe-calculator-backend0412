#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Firebase 连接测试脚本
运行此脚本以验证 Firebase 连接，并在 Firebase 后台写入测试数据
"""

import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

def test_firebase_connection():
    """测试 Firebase 连接并写入测试数据"""
    
    print("=" * 60)
    print("🧪 Firebase 连接测试脚本")
    print("=" * 60)
    
    try:
        # 1. 检查 serviceAccountKey.json
        print("\n📝 步骤 1: 检查服务密钥文件...")
        with open("serviceAccountKey.json", "r") as f:
            key_data = json.load(f)
            project_id = key_data.get("project_id")
            print(f"   ✅ 找到服务密钥文件")
            print(f"   📌 项目 ID: {project_id}")
        
        # 2. 初始化 Firebase
        print("\n📝 步骤 2: 初始化 Firebase...")
        
        # 检查是否已初始化
        if firebase_admin._apps:
            print("   ⚠️  Firebase 已初始化，使用现有实例")
            db = firestore.client()
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("   ✅ Firebase 初始化成功")
        
        # 3. 写入测试数据
        print("\n📝 步骤 3: 写入测试数据到 Firebase...")
        
        test_data = {
            "test_name": "🚀 管道计算器后端测试",
            "status": "✅ 连接成功",
            "message": "这是来自本地测试脚本的数据",
            "timestamp": datetime.now().isoformat(),
            "environment": "local_test",
            "project_id": project_id
        }
        
        # 写入到 Firebase
        db.collection("test").document("local_test_connection").set(test_data)
        print("   ✅ 测试数据已成功写入 Firebase")
        print(f"   📌 集合: test")
        print(f"   📌 文档: local_test_connection")
        
        # 4. 验证数据
        print("\n📝 步骤 4: 验证数据...")
        doc = db.collection("test").document("local_test_connection").get()
        
        if doc.exists:
            print("   ✅ 数据验证成功！")
            print("\n📊 写入的数据:")
            for key, value in doc.to_dict().items():
                print(f"      {key}: {value}")
        else:
            print("   ❌ 数据验证失败")
        
        # 5. 读取所有测试数据
        print("\n📝 步骤 5: 列出所有测试文档...")
        docs = db.collection("test").stream()
        doc_count = 0
        for doc in docs:
            doc_count += 1
            print(f"   - {doc.id}: {doc.to_dict()}")
        
        print(f"\n   ✅ 共找到 {doc_count} 个测试文档")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！Firebase 连接正常")
        print("=" * 60)
        print("\n💡 提示: 现在访问 Firebase 后台可以看到这些数据:")
        print("   1. 打开 Firebase Console")
        print("   2. 选择你的项目")
        print("   3. 进入 Firestore Database")
        print("   4. 查看 'test' 集合")
        print("   5. 你应该能看到 'local_test_connection' 文档")
        
        return True
        
    except FileNotFoundError as e:
        print(f"\n❌ 错误: 找不到文件 - {e}")
        print("   确保 serviceAccountKey.json 在项目根目录")
        return False
    
    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")
        print("\n🔍 故障排除:")
        print("   1. 检查网络连接")
        print("   2. 检查 Firebase 项目是否正常")
        print("   3. 检查 serviceAccountKey.json 权限")
        print("   4. 检查防火墙设置")
        return False

if __name__ == "__main__":
    test_firebase_connection()
