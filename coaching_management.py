"""Coaching center management module: students, courses, enrollments and fee tracking."""

from __future__ import annotations

from datetime import date
import streamlit as st
import pandas as pd

import business_management as bm
import database as db
from ui_utils import show_friendly_error

PAYMENT_METHODS = ["cash", "card", "digital", "bank_transfer", "check"]


def render_coaching_management_page() -> None:
    business = bm.get_current_business_info()
    if not business or business.get("business_type") != "coaching":
        st.warning("This module is available for Coaching Center businesses only.")
        return

    user = st.session_state.get("user")
    user_role = bm.check_business_access(user["id"], business["id"]) if user else None
    if not user_role:
        st.error("You don't have access to this business.")
        return

    st.subheader("Coaching Center")
    summary = db.get_coaching_summary(business["id"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Students", summary["active_students"])
    col2.metric("Active Courses", summary["active_courses"])
    col3.metric("Fee Revenue", f"${summary['fee_revenue']:,.0f}")

    tab_students, tab_courses, tab_fees = st.tabs(["Students", "Courses", "Fee Tracking"])

    with tab_students:
        _render_students(business["id"], user_role)
    with tab_courses:
        _render_courses(business["id"], user_role)
    with tab_fees:
        _render_fees(business["id"], user_role)


def _render_students(business_id: int, user_role: str) -> None:
    if user_role in {"owner", "admin", "staff"}:
        with st.expander("Add Student", expanded=False):
            with st.form("add_student_form"):
                col1, col2 = st.columns(2)
                with col1:
                    student_code = st.text_input("Student Code", placeholder="STD-001")
                    first_name = st.text_input("First Name")
                    email = st.text_input("Email")
                with col2:
                    last_name = st.text_input("Last Name")
                    phone = st.text_input("Phone")
                    guardian_name = st.text_input("Guardian Name")

                if st.form_submit_button("Add Student", use_container_width=True):
                    if not student_code or not first_name or not last_name:
                        st.error("Student code, first name and last name are required.")
                    else:
                        try:
                            db.create_coaching_student(
                                business_id,
                                student_code.strip(),
                                first_name.strip(),
                                last_name.strip(),
                                email.strip() if email else None,
                                phone.strip() if phone else None,
                                guardian_name.strip() if guardian_name else None,
                            )
                            st.success("Student created.")
                            st.rerun()
                        except Exception as exc:
                            show_friendly_error("Unable to add student.", "coaching.add_student", exc)

    students = db.get_coaching_students(business_id, active_only=True)
    if not students:
        st.info("No students yet.")
        return

    df = pd.DataFrame(students)
    show_cols = [c for c in ["student_code", "first_name", "last_name", "email", "phone", "joined_on"] if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)


def _render_courses(business_id: int, user_role: str) -> None:
    if user_role in {"owner", "admin", "staff"}:
        with st.expander("Add Course", expanded=False):
            with st.form("add_course_form"):
                col1, col2 = st.columns(2)
                with col1:
                    course_name = st.text_input("Course Name")
                    instructor_name = st.text_input("Instructor")
                with col2:
                    monthly_fee = st.number_input("Monthly Fee", min_value=0.0, step=1.0)
                    duration_months = st.number_input("Duration (months)", min_value=1, value=3)

                if st.form_submit_button("Add Course", use_container_width=True):
                    if not course_name.strip():
                        st.error("Course name is required.")
                    else:
                        try:
                            db.create_coaching_course(
                                business_id,
                                course_name.strip(),
                                instructor_name.strip() if instructor_name else None,
                                monthly_fee,
                                duration_months,
                            )
                            st.success("Course created.")
                            st.rerun()
                        except Exception as exc:
                            show_friendly_error("Unable to add course.", "coaching.add_course", exc)

    courses = db.get_coaching_courses(business_id, active_only=True)
    if not courses:
        st.info("No courses yet.")
        return

    df = pd.DataFrame(courses)
    show_cols = [c for c in ["course_name", "instructor_name", "monthly_fee", "duration_months"] if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)



def _render_fees(business_id: int, user_role: str) -> None:
    students = db.get_coaching_students(business_id, active_only=True)
    courses = db.get_coaching_courses(business_id, active_only=True)

    if user_role in {"owner", "admin", "staff"} and students and courses:
        with st.expander("Record Fee Payment", expanded=False):
            with st.form("record_fee_form"):
                student = st.selectbox(
                    "Student",
                    options=students,
                    format_func=lambda s: f"{s['student_code']} - {s['first_name']} {s['last_name']}",
                )
                course = st.selectbox("Course", options=courses, format_func=lambda c: c["course_name"])
                col1, col2 = st.columns(2)
                with col1:
                    amount_paid = st.number_input("Amount", min_value=0.0, step=1.0)
                    payment_method = st.selectbox("Payment Method", options=PAYMENT_METHODS)
                with col2:
                    payment_month = st.text_input("Payment Month", value=date.today().strftime("%Y-%m"))
                    notes = st.text_input("Notes")

                if st.form_submit_button("Record Payment", use_container_width=True):
                    try:
                        db.record_coaching_fee_payment(
                            business_id,
                            student["id"],
                            course["id"],
                            amount_paid,
                            payment_month.strip(),
                            payment_method,
                            notes.strip() if notes else None,
                        )
                        st.success("Fee payment recorded.")
                        st.rerun()
                    except Exception as exc:
                        show_friendly_error("Unable to record payment.", "coaching.record_fee", exc)

    payments = db.get_coaching_fee_payments(business_id, limit=200)
    if not payments:
        st.info("No fee payments recorded yet.")
        return

    df = pd.DataFrame(payments)
    show_cols = [c for c in ["payment_date", "student_code", "first_name", "last_name", "course_name", "amount_paid", "payment_method", "payment_month"] if c in df.columns]
    st.dataframe(df[show_cols], use_container_width=True)
