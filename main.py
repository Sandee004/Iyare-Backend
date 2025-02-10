from flask import Flask, request, jsonify
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import timedelta
from datetime import datetime

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "fish"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=24)

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    phoneNumber = db.Column(db.String(20), nullable=False, unique=True)
    nextOfKinName = db.Column(db.String(50), nullable=False)
    nextOfKinPhoneNumber = db.Column(db.String(20), nullable=False)


class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    departure_city = db.Column(db.String(100), nullable=False)
    destination_city = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    estimated_time = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "departure_city": self.departure_city,
            "destination_city": self.destination_city,
            "price": self.price,
            "estimated_time": self.estimated_time
        }


class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey("route.id"), nullable=False)
    bus_name = db.Column(db.String(100), nullable=False)
    total_seats = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.String(50), nullable=False)

    route = db.relationship("Route", backref=db.backref("buses", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "bus_name": self.bus_name,
            "total_seats": self.total_seats,
            "available_seats": self.available_seats,
            "departure_time": self.departure_time,
            "route_id": self.route_id
        }


class Seat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey("bus.id"), nullable=False)
    seat_number = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default="available")  # "available" or "booked"
    user_id = db.Column(db.Integer, nullable=True)  # Nullable for guest booking


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    next_of_kin_name = db.Column(db.String(100), nullable=False)
    next_of_kin_phone = db.Column(db.String(20), nullable=False)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    seat_numbers = db.Column(db.String(255), nullable=False)  # Example: "1,2,3"
    departure_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_name": self.user_name,
            "phone_number": self.phone_number,
            "next_of_kin_name": self.next_of_kin_name,
            "next_of_kin_phone": self.next_of_kin_phone,
            "bus_id": self.bus_id,
            "seat_numbers": self.seat_numbers,
            "departure_date": str(self.departure_date),
        }


@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    required_fields = ["name", "email", "phoneNumber", "nextOfKinName", "nextOfKinPhoneNumber"]

    if not all(data.get(field) for field in required_fields):
        return jsonify({"message": "Fill all fields"}), 400

    if Users.query.filter_by(email=data["email"]).first():
        return jsonify({"message": "Email is already in use"}), 400

    if Users.query.filter_by(phoneNumber=data["phoneNumber"]).first():
        return jsonify({"message": "Phone number is already in use"}), 400

    new_user = Users(**data)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = Users.query.filter_by(email=data['email']).first()

    if user:
        access_token = create_access_token(identity=user.id)
        return jsonify({
            "access_token": access_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phoneNumber": user.phoneNumber
            }
        })

    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/api/routes", methods=["GET"])
def get_routes():
    routes = Route.query.all()
    
    if not routes:
        return jsonify({"message": "No routes available"}), 404
    
    return jsonify([route.to_dict() for route in routes]), 200


def seed_routes():
    default_routes = [
        {"departure_city": "Lagos-Ipaja", "destination_city": "Benin city", "price": 15000, "estimated_time": "10 hours"},
        {"departure_city": "Benin city", "destination_city": "Lagos-Ipaja", "price": 12000, "estimated_time": "8 hours"},
        {"departure_city": "Delta", "destination_city": "Lagos-Agege", "price": 18000, "estimated_time": "12 hours"}
    ]

    for route in default_routes:
        existing_route = Route.query.filter_by(
            departure_city=route["departure_city"],
            destination_city=route["destination_city"]
        ).first()

        if not existing_route:
            new_route = Route(**route)
            db.session.add(new_route)
    print("New routes added successfully")
    db.session.commit()


@app.route("/api/buses/<int:route_id>", methods=["GET"])
def get_buses(route_id):
    buses = Bus.query.filter_by(route_id=route_id).all()
    
    if not buses:
        return jsonify({"message": "No buses available for this route"}), 404
    
    return jsonify([bus.to_dict() for bus in buses]), 200

def seed_buses():
    if not Bus.query.first():
        buses = [
            {"route_id": 1, "bus_name": "Coach", "total_seats": 20, "available_seats": 20, "departure_time": "7:00am"},
            {"route_id": 1, "bus_name": "Jet Movers", "total_seats": 14, "available_seats": 14, "departure_time": "8:30am"},
            {"route_id": 2, "bus_name": "Hiace", "total_seats": 14, "available_seats": 14, "departure_time": "10:00am"},
            {"route_id": 2, "bus_name": "Hiace", "total_seats": 25, "available_seats": 25, "departure_time": "12:00pm"},
        ]
        for bus in buses:
            new_bus = Bus(**bus)
            db.session.add(new_bus)
        db.session.commit()


@app.route("/api/buses/<int:bus_id>/seats", methods=["GET"])
def get_seats(bus_id):
    seats = Seat.query.filter_by(bus_id=bus_id).all()
    return jsonify([
        {"id": seat.id, "seat_number": seat.seat_number, "status": seat.status}
        for seat in seats
    ])

@app.route("/api/book-seat", methods=["POST"])
@jwt_required()
def book_seat():
    data = request.json
    seat_numbers = data.get("seats", [])  
    bus_id = data.get("busId")

    if not bus_id or not seat_numbers:
        return jsonify({"message": "Missing bus ID or seats"}), 400

    if isinstance(bus_id, str) and bus_id.isdigit():
        bus_id = int(bus_id)

    seats = Seat.query.filter(Seat.bus_id == bus_id, Seat.seat_number.in_(seat_numbers)).all()

    if len(seats) != len(seat_numbers):
        return jsonify({"message": "Some seats are already booked or do not exist"}), 400

    for seat in seats:
        seat.status = "booked"

    db.session.commit()

    return jsonify({"message": "Seats booked successfully!"}), 200


def seed_seats():
    if not Seat.query.first():
        buses = Bus.query.all()
        seats = []

        for bus in buses:
            for seat_number in range(1, bus.total_seats + 1):
                seats.append(Seat(bus_id=bus.id, seat_number=seat_number, status="available"))

        db.session.bulk_save_objects(seats)
        db.session.commit()
        print("Seats seeded successfully!")


@app.route("/api/confirm-booking", methods=["POST"])
def confirm_booking():
    data = request.json
    bus_id = data.get("busId")
    seat_numbers = data.get("seats")
    departure_date = data.get("departureDate")

    
    try:
        departure_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    seat_list = seat_numbers.split(",") if seat_numbers else []
    seats = Seat.query.filter(Seat.bus_id == bus_id, Seat.seat_number.in_(seat_list)).all()

    if len(seats) != len(seat_list):
        return jsonify({"error": "Some seats are already booked or do not exist"}), 400

    booking = Booking(
        user_name=data.get("name"),
        phone_number=data.get("phoneNumber"),
        next_of_kin_name=data.get("nextOfKinName"),
        next_of_kin_phone=data.get("nextOfKinPhoneNumber"),
        bus_id=bus_id,
        seat_numbers=seat_numbers,
        departure_date=departure_date,
    )

    for seat in seats:
        seat.status = "booked"

    db.session.add(booking)
    db.session.commit()

    return jsonify({"message": "Booking successful!", "booking": booking.to_dict()}), 201

@app.route("/api/user", methods=["GET"])
@jwt_required()
def get_user():
    user_id = get_jwt_identity()
    user = Users.query.get(user_id)
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    return jsonify({
        "user": {
            "name": user.name,
            "phoneNumber": user.phone_number,
            "nextOfKinName": user.next_of_kin_name,
            "nextOfKinPhoneNumber": user.next_of_kin_phone_number,
        }
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_routes()
        seed_buses()
        seed_seats()

    app.run(debug=True)
