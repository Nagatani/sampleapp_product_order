from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import Order, User, Product
from peewee import *
from datetime import datetime, timedelta

# Blueprintの作成
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 現在の月を含む過去12か月の「YYYY-MM」リストを生成
def get_past_year_months():
    current_date = datetime.now()
    year_months = [(current_date.year, current_date.month)]
    for _ in range(11):  # 過去11か月分
        current_date = current_date.replace(day=1) - timedelta(days=1)
        year_months.append((current_date.year, current_date.month))
    return [f'{year}-{month:02}' for year, month in reversed(year_months)]


@api_bp.route('/ym_summary', methods=['GET', 'POST'])
def ym_summery():
    # Peeweeクエリの実行
    query = (
        Order.select(
            fn.strftime('%Y-%m', Order.order_date).alias('year_month'),
            fn.SUM(Product.price).alias('total_amount')
        )
        .join(Product, JOIN.LEFT_OUTER)
        .group_by(fn.strftime('%Y-%m', Order.order_date))
        .order_by(fn.strftime('%Y-%m', Order.order_date))
    )
    # クエリ結果を辞書に変換
    sales_data = {result.year_month: result.total_amount for result in query}
    # 過去12か月分の年月リストを取得
    past_year_months = get_past_year_months()
    # 過去12か月のデータを統合（売上がない月は0とする）
    merged_data = {month: sales_data.get(month, 0) for month in past_year_months}

    # 年月（labels）と売上金額（data）を分離
    result = {
        'labels': list(merged_data.keys()),
        'data': list(merged_data.values())
    }

    return jsonify(result)


@api_bp.route('/user_ranking', methods=['GET', 'POST'])
def user_ranking():
    query = (
        Order.select(
            User.name,  # 顧客名
            fn.SUM(Product.price).alias('total_sales')  # 売上合計
        )
        .join(User, on=(Order.user == User.id))  # 明示的にUserとの結合条件を指定
        .join(Product, on=(Order.product == Product.id))  # 明示的にProductとの結合条件を指定
        .group_by(Order.user)  # 顧客ごとにグループ化
        .order_by(fn.SUM(Product.price).desc())  # 売上が多い順にソート
    )

    # 上位10名の結果を表示
    sales_data = { f'rank {rank}:{result.user.name}' : result.total_sales for rank, result in enumerate(query.limit(5), start=1)}
    
    result = {
        'labels': list(sales_data.keys()),
        'data': list(sales_data.values())
    }
    return jsonify(result)


@api_bp.route('/month_total_by_product', methods=['GET', 'POST'])
def month_total_by_product():
        
    # 今月の開始日と終了日を取得
    current_date = datetime.now()
    start_of_month = current_date.replace(day=1)
    end_of_month = (current_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # 製品別の売上合計を集計するクエリ
    query = (
        Order.select(
            Product.name,  # 製品名
            fn.SUM(Product.price).alias('total_sales')  # 売上金額を合計
        )
        .join(Product, JOIN.LEFT_OUTER)  # Productテーブルを結合
        .where(
            (Order.order_date >= start_of_month) & 
            (Order.order_date <= end_of_month)
        )
        .group_by(Order.product)
        .order_by(fn.SUM(Product.price).desc())  # 売上金額が多い順にソート
    )

    # クエリ結果を辞書に変換
    sales_data = {result.product.name: result.total_sales for result in query}

    result = {
        'labels': list(sales_data.keys()),
        'data': list(sales_data.values())
    }
    
    return jsonify(result)


