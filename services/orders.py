"""Бизнес-логика заказов: создание, статусы, чеки."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database import get_session
from models import Order, OrderItem, OrderStatus, Payment, PaymentStatus, Product, ReceiptType


async def create_order(user_id: int, product: Product, variant, quantity: int) -> Order:
    """Создаёт заказ с одной позицией (MVP-модель — один товар за заказ)."""
    unit_price = Decimal(product.price)
    if variant is not None:
        unit_price += Decimal(variant.price_modifier)

    async with get_session() as session:
        order = Order(user_id=user_id, status=OrderStatus.NEW, total_amount=unit_price * quantity)
        session.add(order)
        await session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            variant_id=variant.id if variant else None,
            product_name=product.name if not variant else f"{product.name} ({variant.name})",
            quantity=quantity,
            price=unit_price,
        )
        session.add(item)
        await session.commit()
        await session.refresh(order)
        return order


async def set_address(order_id: int, address: str) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.address = address
            order.status = OrderStatus.WAITING_PAYMENT
            await session.commit()


async def set_payment_method(order_id: int, payment_method_id: int) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.payment_method_id = payment_method_id
            await session.commit()


async def attach_receipt(order_id: int, file_id: str, receipt_type: ReceiptType) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if not order:
            return
        result = await session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if payment is None:
            payment = Payment(order_id=order_id)
            session.add(payment)
        payment.receipt_file_id = file_id
        payment.receipt_type = receipt_type
        payment.status = PaymentStatus.PENDING
        order.status = OrderStatus.PAYMENT_CHECK
        await session.commit()


async def confirm_payment(order_id: int, admin_tg_id: int) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        result = await session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.PAID
        if payment:
            payment.status = PaymentStatus.CONFIRMED
            payment.confirmed_by = admin_tg_id
            payment.confirmed_at = datetime.now(timezone.utc)
        await session.commit()


async def reject_payment(order_id: int, admin_tg_id: int) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        result = await session.execute(select(Payment).where(Payment.order_id == order_id))
        payment = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.REJECTED
        if payment:
            payment.status = PaymentStatus.REJECTED
            payment.confirmed_by = admin_tg_id
            payment.confirmed_at = datetime.now(timezone.utc)
        await session.commit()


async def set_status(order_id: int, status: OrderStatus) -> None:
    async with get_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = status
            await session.commit()


async def cancel_order(order_id: int) -> None:
    await set_status(order_id, OrderStatus.CANCELLED)


async def get_order(order_id: int) -> Order | None:
    async with get_session() as session:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.payment_method), selectinload(Order.user))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def list_user_orders(user_id: int) -> list[Order]:
    async with get_session() as session:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def list_orders_by_status(status: OrderStatus) -> list[Order]:
    async with get_session() as session:
        stmt = (
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
            .options(selectinload(Order.items))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def count_orders() -> dict:
    async with get_session() as session:
        total = (await session.execute(select(func.count(Order.id)))).scalar_one()
        completed = (
            await session.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED))
        ).scalar_one()
        pending = (
            await session.execute(
                select(func.count(Order.id)).where(
                    Order.status.in_(
                        [OrderStatus.NEW, OrderStatus.WAITING_PAYMENT, OrderStatus.PAYMENT_CHECK, OrderStatus.PAID, OrderStatus.PROCESSING]
                    )
                )
            )
        ).scalar_one()
        return {"total": total, "completed": completed, "pending": pending}
