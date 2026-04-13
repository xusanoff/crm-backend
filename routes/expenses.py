from datetime import date
from flask              import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from models             import db
from models.user        import User
from models.expense     import Expense
from models.payment     import Payment
from utils.utils        import get_response
from utils.decorators   import role_required
from sqlalchemy         import func

expense_bp = Blueprint("expense", __name__, url_prefix="/api/expenses")

VALID_CATEGORIES = {"ijara", "maosh", "jihozlar", "kommunal", "marketing", "boshqa"}


@expense_bp.route("", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def expense_list():
    """
    Barcha harajatlar.
    ?from=YYYY-MM-DD&to=YYYY-MM-DD orqali sana bo'yicha filter
    """
    from_date = request.args.get("from")
    to_date   = request.args.get("to")

    query = Expense.query

    if from_date:
        try:
            query = query.filter(Expense.expense_date >= date.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            query = query.filter(Expense.expense_date <= date.fromisoformat(to_date))
        except ValueError:
            pass

    expenses = query.order_by(Expense.expense_date.desc()).all()
    result   = [Expense.to_dict(e) for e in expenses]
    return get_response("Expense List", result, 200), 200


@expense_bp.route("", methods=["POST"])
@role_required(["ADMIN", "MANAGER"])
def expense_create():
    """
    Yangi harajat kiritish.
    Body: { "amount": 500000, "description": "Ijara to'lovi", "category": "ijara", "expense_date": "2025-03-01" }
    """
    user_id     = int(get_jwt_identity())
    data        = request.get_json()
    amount      = data.get("amount")
    description = data.get("description")
    category    = (data.get("category") or "boshqa").lower()
    expense_date_str = data.get("expense_date")

    if not amount or not description:
        return get_response("amount va description majburiy", None, 400), 400

    try:
        exp_date = date.fromisoformat(expense_date_str) if expense_date_str else date.today()
    except ValueError:
        return get_response("Noto'g'ri sana formati. YYYY-MM-DD ishlating", None, 400), 400

    new_expense = Expense(
        amount       = float(amount),
        description  = description,
        category     = category,
        expense_date = exp_date,
        created_by   = user_id
    )
    db.session.add(new_expense)
    db.session.commit()
    return get_response("Harajat muvaffaqiyatli kiritildi", Expense.to_dict(new_expense), 200), 200


@expense_bp.route("/<int:expense_id>", methods=["DELETE"])
@role_required(["ADMIN"])
def expense_delete(expense_id):
    """Faqat ADMIN o'chira oladi"""
    expense = Expense.query.filter_by(id=expense_id).first()
    if not expense:
        return get_response("Harajat topilmadi", None, 404), 404

    db.session.delete(expense)
    db.session.commit()
    return get_response("Harajat o'chirildi", None, 200), 200


@expense_bp.route("/summary", methods=["GET"])
@role_required(["ADMIN", "MANAGER"])
def expense_summary():
    """
    Moliyaviy hisobot:
    - Jami to'lovlar (kirim)
    - Jami harajatlar (chiqim)
    - Sof foyda
    - Kategoriya bo'yicha harajatlar
    """
    from_date = request.args.get("from")
    to_date   = request.args.get("to")

    # To'lovlar (kirim)
    pay_query = db.session.query(func.sum(Payment.amount).label("total"))
    # Harajatlar (chiqim)
    exp_query = Expense.query

    if from_date:
        try:
            fd = date.fromisoformat(from_date)
            pay_query = pay_query.filter(Payment.payment_date >= fd)
            exp_query = exp_query.filter(Expense.expense_date >= fd)
        except ValueError:
            pass
    if to_date:
        try:
            td = date.fromisoformat(to_date)
            pay_query = pay_query.filter(Payment.payment_date <= td)
            exp_query = exp_query.filter(Expense.expense_date <= td)
        except ValueError:
            pass

    total_income  = float(pay_query.scalar() or 0)
    expenses      = exp_query.all()
    total_expense = sum(e.amount for e in expenses)
    net_profit    = total_income - total_expense

    # Kategoriya bo'yicha
    by_category = {}
    for e in expenses:
        cat = e.category or "boshqa"
        by_category[cat] = by_category.get(cat, 0) + e.amount

    return get_response("Moliyaviy hisobot", {
        "total_income":   total_income,
        "total_expense":  total_expense,
        "net_profit":     net_profit,
        "by_category":    by_category,
        "expense_count":  len(expenses),
    }, 200), 200
