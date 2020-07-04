from collections import defaultdict
from datetime import datetime


class Group():
    def __init__(self, name):
        self.name = name  # primary key


class User():
    def __init__(self, phone, other_details={}):
        self.phone = phone  # primary key
        self.email = other_details.get('email')
        self.name = other_details.get('name')


class Expense:
    PERCENTAGE_BASED = 'PERCENTAGE_BASED'
    AMOUNT_BASED = 'AMOUNT_BASED'

    def __init__(self, group_id, category, what_for, total, split_type, payment_map, share_map, recorded_by):
        self.group_id = group_id
        self.category = category
        self.what_for = what_for
        self.total = total
        self.recorded_by = recorded_by
        self.recorded_at = datetime.now()
        self.split_type = split_type  # percentage_based, amount_based
        self.payment_map = payment_map
        self.share_map = share_map


class Transaction():
    def __init__(self, source_type, source_id, group_id, amount, owner_id):
        self.group_id = group_id
        self.source_type = source_type
        self.source_id = source_id
        self.amount = amount
        self.owner_id = owner_id


class Settlement():
    def __init__(self, group_id, payer_user_id, receiver_user_id, amount):
        self.group_id = group_id
        self.amount = amount
        self.payer_user_id = payer_user_id
        self.receiver_user_id = receiver_user_id
        self.payer_transaction_id = None
        self.receiver_transaction_id = None


class SingletonMetaClass(type):
    def __init__(cls, name, bases, dict):
        super(SingletonMetaClass, cls) \
            .__init__(name, bases, dict)
        original_new = cls.__new__

        def my_new(cls, *args, **kwds):
            if cls.instance == None:
                cls.instance = \
                    original_new(cls, *args, **kwds)
            return cls.instance

        cls.instance = None
        cls.__new__ = staticmethod(my_new)


class GroupManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.group_id_to_groups = {}
        self.group_id_to_user_ids = defaultdict(list)
        self.group_id_to_expenses_ids = defaultdict(list)
        self.group_id_to_settlement_ids = defaultdict(list)
        self.expense_manager = ExpenseManager()
        self.user_manager = UserManager()
        self.settlement_manager = SettlementManager()

    def create_group(self, name):
        if not name:
            raise Exception("group name is required.")
        if name in self.group_id_to_groups:
            raise Exception("group with this name already exists.")
        g = Group(name=name)
        self.group_id_to_groups[id(g)] = g
        return id(g)

    def add_user_to_group(self, group_id, user_id):
        if group_id not in GroupManager.instance.group_id_to_groups:
            raise Exception("group not exists.")
        if not self.user_manager.get_user_by_id(user_id):
            raise Exception("user not exists.")
        if user_id in self.group_id_to_user_ids[group_id]:
            raise Exception("User already part of the group.")
        if group_id not in self.group_id_to_user_ids:
            self.group_id_to_user_ids[group_id] = []
        self.group_id_to_user_ids[group_id].append(user_id)

    def get_group_by_id(self, group_id):
        if group_id not in self.group_id_to_groups:
            raise Exception("group not exists.")
        return self.group_id_to_groups.get(group_id)

    def add_expense_in_group(self, group_id, category, what_for, total, split_type, payment_map, share_map, recorded_by):
        if not GroupManager.instance.get_group_by_id(group_id):
            raise Exception("group doesn't exist.")
        if not recorded_by:
            raise Exception("recorded_by must be present exist.")
        if recorded_by and recorded_by not in self.group_id_to_user_ids[group_id]:
            raise Exception("recording user not part of the group.")
        if total <= 0:
            raise Exception("Expense amount must be greater than 0")
        self.group_id_to_expenses_ids[group_id].append(self.expense_manager.create(group_id, category, what_for, total, split_type, payment_map, share_map, recorded_by))

    def add_settlement(self, group_id, payer_user_id, receiver_user_id, amount):
        if amount<=0:
            raise Exception("amount should be greater than 0.")
        if not GroupManager.instance.get_group_by_id(group_id):
            raise Exception("group doesn't exist.")
        if not payer_user_id:
            raise Exception("payer_user_id must be present exist.")
        if payer_user_id and payer_user_id not in self.group_id_to_user_ids[group_id]:
            raise Exception("payer_user_id  not part of the group.")
        if not receiver_user_id:
            raise Exception("receiver_user_id must be present exist.")
        if receiver_user_id and receiver_user_id not in self.group_id_to_user_ids[group_id]:
            raise Exception("receiver_user_id not part of the group.")
        user_id_to_balance = self.get_user_wise_balance_for_group(group_id)
        if payer_user_id not in user_id_to_balance:
            raise Exception("No balance for payer_user_id in group.")
        if receiver_user_id not in user_id_to_balance:
            raise Exception("No balance for receiver_user_id in group.")
        payer_liability = -user_id_to_balance[payer_user_id]
        if payer_liability < 0:
            raise Exception("payer_user_id doesn't owe anything to anyone.")
        if amount > payer_liability:
            raise Exception("payer_user_id owes only %s in group"%(payer_liability))
        receiver_receivables = user_id_to_balance[receiver_user_id]
        if receiver_receivables < 0:
            raise Exception("receiver_user_id doesn't have any receivables.")
        if receiver_receivables < amount:
            raise Exception("receiver_user_id has receivables worth only %s in group" % (receiver_receivables))
        self.group_id_to_settlement_ids[group_id].append(self.settlement_manager.create(group_id, payer_user_id, receiver_user_id, amount))

    def get_user_wise_balance_for_group(self, group_id):
        expense_ids = self.group_id_to_expenses_ids[group_id]
        user_id_to_balance = {}
        for expense_id in expense_ids:
            user_id_to_balance_for_expense = self.expense_manager.get_user_wise_balance_for_expense(expense_id)
            for user_id, balance in user_id_to_balance_for_expense.items():
                if user_id not in user_id_to_balance:
                    user_id_to_balance[user_id] = 0.0
                user_id_to_balance[user_id]+=balance
        settlement_ids = self.group_id_to_settlement_ids[group_id]
        for settlement_id in settlement_ids:
            user_id_to_amount = self.settlement_manager.get_user_wise_amount_for_settlement(settlement_id)
            for user_id, amount in user_id_to_amount.items():
                if user_id not in user_id_to_balance:
                    user_id_to_balance[user_id] = 0.0
                user_id_to_balance[user_id]+=amount
        return user_id_to_balance


class UserManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.user_id_to_users = {}

    def get_user_by_id(self, id):
        return self.user_id_to_users.get(id)

    def create_user(self, user_details):
        if not user_details.get('phone'):
            raise Exception("user phone is required.")
        if user_details.get('phone') in self.user_id_to_users:
            raise Exception("user with phone already exists.")
        u = User(phone=user_details.pop('phone'),
             other_details=user_details)
        self.user_id_to_users[id(u)] = u
        return id(u)


class TransactionManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.transaction_id_to_transactions = {}

    def get_transaction_by_id(self, transaction_id):
        if transaction_id not in self.transaction_id_to_transactions:
            raise Exception("Invalid transaction_id.")
        return self.transaction_id_to_transactions[transaction_id]

    def create(self, source_type, source_id, group_id, amount, owner_id):
        t = Transaction(source_type=source_type, source_id=source_id, group_id=group_id, amount=amount,
                        owner_id=owner_id)
        self.transaction_id_to_transactions[id(t)] = t
        return id(t)

    def get_user_id_and_amount(self, transaction_id):
        t = self.get_transaction_by_id(transaction_id)
        return [t.owner_id, t.amount]


class ExpenseManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.expense_id_to_expenses = {}
        self.expense_id_to_transaction_ids = {}
        self.transaction_manager = TransactionManager()

    def get_expense_by_id(self, expense_id):
        if expense_id not in self.expense_id_to_expenses:
            raise Exception("Invalid expense_id.")
        return self.expense_id_to_expenses[expense_id]

    def create(self, group_id, category, what_for, total, split_type, payment_map, share_map, recorded_by):
        expense = Expense(group_id=group_id, category=category, what_for=what_for, total=total, split_type=split_type, payment_map=payment_map, share_map=share_map,
                          recorded_by=recorded_by)
        user_to_paid, user_to_share = self.validate(expense)
        transaction_ids = []
        for user_id, payment_amount in user_to_paid.items():
            transaction_ids.append(
                self.transaction_manager.create(expense.__class__.__name__, id(expense), group_id, payment_amount, user_id))
        for user_id, share_amount in user_to_share.items():
            transaction_ids.append(
                self.transaction_manager.create(expense.__class__.__name__, id(expense), group_id, -share_amount, user_id))
        self.expense_id_to_expenses[id(expense)] = expense
        self.expense_id_to_transaction_ids[id(expense)] = transaction_ids
        return id(expense)

    def validate(self, expense):
        user_to_paid = {}
        user_to_share = {}
        if expense.split_type == expense.PERCENTAGE_BASED:
            tp = 0
            for user_id, paid_percentage in expense.payment_map.items():
                user_to_paid[user_id] = round(expense.total * (paid_percentage / 100), 2)
                tp += paid_percentage
            if tp != 100:
                raise Exception("Payment Percentages should add upto 100.")
            ts = 0
            for user_id, share_percentage in expense.share_map.items():
                user_to_share[user_id] = round(expense.total * (share_percentage / 100), 2)
                ts += share_percentage
            if ts != 100:
                raise Exception("Share Percentages should add upto 100.")
        elif expense.split_type == expense.AMOUNT_BASED:
            user_to_paid = expense.payment_map
            user_to_share = expense.share_map
            if sum(user_to_paid.values()) != expense.total:
                raise Exception("Payment amounts don't add upto total.")
            if sum(user_to_share.values()) != expense.total:
                raise Exception("Share amounts don't add upto total.")
        else:
            raise Exception("Invalid split_type.")
        return user_to_paid, user_to_share

    def get_user_wise_balance_for_expense(self, expense_id):
        expense = self.get_expense_by_id(expense_id)
        transaction_ids = self.expense_id_to_transaction_ids[expense_id]
        if not transaction_ids:
            return {}
        response = {}
        for transaction_id in transaction_ids:
            user_id, amount = self.transaction_manager.get_user_id_and_amount(transaction_id)
            if user_id not in response:
                response[user_id] = 0.0
            response[user_id]+=amount
        return response


class SettlementManager(metaclass=SingletonMetaClass):
    def __init__(self):
        self.settlement_id_to_settlements = {}
        self.transaction_manager = TransactionManager()

    def get_settlement_by_id(self, settlement_id):
        if settlement_id not in self.settlement_id_to_settlements:
            raise Exception("Invalid settlement_id.")
        return self.settlement_id_to_settlements[settlement_id]

    def create(self, group_id, payer_user_id, receiver_user_id, amount):
        settlement = Settlement(group_id=group_id, payer_user_id=payer_user_id, receiver_user_id=receiver_user_id,
                                amount=amount)
        settlement.payer_transaction_id = id(
            self.transaction_manager.create(settlement.__class__.__name__, id(settlement), group_id, amount, payer_user_id))
        settlement.receiver_transaction_id = id(
            self.transaction_manager.create(settlement.__class__.__name__, group_id, id(settlement), -amount, receiver_user_id))
        self.settlement_id_to_settlements[id(settlement)] = settlement
        return id(settlement)

    def get_user_wise_amount_for_settlement(self, settlement_id):
        settlement = self.get_settlement_by_id(settlement_id)
        return {} if not settlement else {settlement.payer_user_id: settlement.amount, settlement.receiver_user_id: -settlement.amount}

###commands:
def master():
    G = GroupManager()
    U = UserManager()
    group_id = G.create_group("Home")
    u1 = U.create_user({"name": "vishal", "phone": "9911505479"})
    u2 = U.create_user({"name": "vivek", "phone": "9911505470"})
    u3 = U.create_user({"name": "vineet", "phone": "9911505478"})

    G.add_user_to_group(group_id, u1)
    G.add_user_to_group(group_id, u2)
    G.add_user_to_group(group_id, u3)

    G.add_expense_in_group(group_id, "Food", "groceries", 500, "AMOUNT_BASED", {u1: 500}, {u1: 125, u2: 225, u3: 150}, u1)
    G.add_expense_in_group(group_id, "Food", "groceries", 800, "PERCENTAGE_BASED", {u2: 100}, {u1: 20, u2: 30, u3: 50}, u2)

    user_wise_balance = G.get_user_wise_balance_for_group(group_id)
    print(user_wise_balance)
    assert (500-125 -160) == user_wise_balance[u1]

    # G.add_settlement(group_id, u1, u2, 100)

    G.add_settlement(group_id, u3, u2, 335)

    user_wise_balance = G.get_user_wise_balance_for_group(group_id)
    print(user_wise_balance)





if __name__ == '__main__':
    master()
