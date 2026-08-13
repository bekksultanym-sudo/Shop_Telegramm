"""Отзывы: публикация, модерация."""
from __future__ import annotations

from sqlalchemy import select

from database import get_session
from models import Order, OrderStatus, Review


async def list_published() -> list[Review]:
    async with get_session() as session:
        stmt = (
            select(Review)
            .where(Review.is_published.is_(True))
            .order_by(Review.is_pinned.desc(), Review.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def list_all() -> list[Review]:
    async with get_session() as session:
        stmt = select(Review).order_by(Review.is_pinned.desc(), Review.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_review(review_id: int) -> Review | None:
    async with get_session() as session:
        return await session.get(Review, review_id)


async def has_completed_order_without_review(user_id: int) -> int | None:
    """Возвращает ID завершённого заказа без отзыва, если есть."""
    async with get_session() as session:
        stmt = select(Order).where(Order.user_id == user_id, Order.status == OrderStatus.COMPLETED)
        result = await session.execute(stmt)
        for order in result.scalars().all():
            review_check = await session.execute(select(Review).where(Review.order_id == order.id))
            if review_check.scalar_one_or_none() is None:
                return order.id
        return None


async def create_review(user_id: int, order_id: int | None, text: str, rating: int | None) -> Review:
    async with get_session() as session:
        review = Review(user_id=user_id, order_id=order_id, text=text, rating=rating, is_published=False)
        session.add(review)
        await session.commit()
        await session.refresh(review)
        return review


async def set_published(review_id: int, published: bool) -> None:
    async with get_session() as session:
        review = await session.get(Review, review_id)
        if review:
            review.is_published = published
            await session.commit()


async def set_pinned(review_id: int, pinned: bool) -> None:
    async with get_session() as session:
        review = await session.get(Review, review_id)
        if review:
            review.is_pinned = pinned
            await session.commit()


async def delete_review(review_id: int) -> None:
    async with get_session() as session:
        review = await session.get(Review, review_id)
        if review:
            await session.delete(review)
            await session.commit()
