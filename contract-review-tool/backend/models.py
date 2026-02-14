import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_text = Column(Text, nullable=False)
    category = Column(String(100), default="未分类")
    status = Column(String(50), default="pending")  # pending, analyzing, completed, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reviews = relationship("ReviewItem", back_populates="contract", cascade="all, delete-orphan")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    location = Column(String(500), nullable=False)      # 哪里需要修改
    original_text = Column(Text, nullable=False)         # 原文
    suggested_text = Column(Text, nullable=False)        # 修改成什么
    reason = Column(Text, nullable=False)                # 原因
    severity = Column(String(50), default="warning")     # info, warning, critical

    contract = relationship("Contract", back_populates="reviews")


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, nullable=False)
