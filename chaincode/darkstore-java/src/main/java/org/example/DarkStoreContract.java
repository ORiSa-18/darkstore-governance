package org.example;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.hyperledger.fabric.contract.Context;
import org.hyperledger.fabric.contract.ContractInterface;
import org.hyperledger.fabric.contract.annotation.Contact;
import org.hyperledger.fabric.contract.annotation.Contract;
import org.hyperledger.fabric.contract.annotation.Default;
import org.hyperledger.fabric.contract.annotation.Info;
import org.hyperledger.fabric.contract.annotation.License;
import org.hyperledger.fabric.contract.annotation.Transaction;
import org.hyperledger.fabric.shim.ChaincodeException;
import org.hyperledger.fabric.shim.ChaincodeStub;
import org.hyperledger.fabric.shim.ledger.CompositeKey;
import org.hyperledger.fabric.shim.ledger.KeyValue;
import org.hyperledger.fabric.shim.ledger.QueryResultsIterator;

@Contract(
    name = "DarkStoreContract",
    info = @Info(
        title = "Dark Store Event Logging Contract",
        description = "Records fulfillment events and verifies SLA compliance for quick-commerce orders.",
        version = "1.0.0",
        license = @License(name = "Apache-2.0"),
        contact = @Contact(name = "Example Org")
    )
)
@Default
public class DarkStoreContract implements ContractInterface {

    private static final String EVENT_OBJECT_TYPE = "orderEvent";
    private static final String VIOLATION_OBJECT_TYPE = "slaViolation";

    private static final String ORDER_PLACED = "ORDER_PLACED";
    private static final String ORDER_PICKED = "ORDER_PICKED";
    private static final String ORDER_PACKED = "ORDER_PACKED";
    private static final String ORDER_DISPATCHED = "ORDER_DISPATCHED";
    private static final String ORDER_DELIVERED = "ORDER_DELIVERED";
    private static final String SLA_VIOLATION_EVENT = "SLA_VIOLATION";

    private static final String NO_VIOLATION = "NONE";
    private static final String PICKING_SLA_BREACH = "PICKING_SLA_BREACH";
    private static final String PACKING_SLA_BREACH = "PACKING_SLA_BREACH";
    private static final String DISPATCH_SLA_BREACH = "DISPATCH_SLA_BREACH";
    private static final String DELIVERY_SLA_BREACH = "DELIVERY_SLA_BREACH";

    private static final long PICKING_SLA_MILLIS = 3L * 60L * 1000L;
    private static final long PACKING_SLA_MILLIS = 10L * 60L * 1000L;
    private static final long DISPATCH_SLA_MILLIS = 5L * 60L * 1000L;
    private static final long DELIVERY_SLA_MILLIS = 30L * 60L * 1000L;

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public OrderEvent recordOrderPlaced(final Context ctx, final String orderId, final String storeId,
            final long timestamp) {
        return recordOrderEvent(ctx, orderId, storeId, timestamp, ORDER_PLACED);
    }

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public OrderEvent recordOrderPicked(final Context ctx, final String orderId, final String storeId,
            final long timestamp) {
        return recordOrderEvent(ctx, orderId, storeId, timestamp, ORDER_PICKED);
    }

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public OrderEvent recordOrderPacked(final Context ctx, final String orderId, final String storeId,
            final long timestamp) {
        return recordOrderEvent(ctx, orderId, storeId, timestamp, ORDER_PACKED);
    }

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public OrderEvent recordOrderDispatched(final Context ctx, final String orderId, final String storeId,
            final long timestamp) {
        return recordOrderEvent(ctx, orderId, storeId, timestamp, ORDER_DISPATCHED);
    }

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public OrderEvent recordOrderDelivered(final Context ctx, final String orderId, final String storeId,
            final long timestamp) {
        return recordOrderEvent(ctx, orderId, storeId, timestamp, ORDER_DELIVERED);
    }

    @Transaction(intent = Transaction.TYPE.EVALUATE)
    public OrderEvent[] queryOrderHistory(final Context ctx, final String orderId) {
        validateRequired(orderId, "orderId");

        final List<OrderEvent> events = getAllOrderEvents(ctx, orderId);
        events.sort(Comparator.comparingLong(OrderEvent::getTimestamp));
        return events.toArray(new OrderEvent[0]);
    }

    @Transaction(intent = Transaction.TYPE.EVALUATE)
    public ViolationRecord[] queryViolation(final Context ctx, final String orderId) {
        validateRequired(orderId, "orderId");
        return getViolationRecords(ctx, orderId).toArray(new ViolationRecord[0]);
    }

    @Transaction(intent = Transaction.TYPE.EVALUATE)
    public ViolationRecord[] queryAllViolations(final Context ctx) {
        return getViolationRecords(ctx, null).toArray(new ViolationRecord[0]);
    }

    @Transaction(intent = Transaction.TYPE.SUBMIT)
    public SLAResult verifySLA(final Context ctx, final String orderId) {
        validateRequired(orderId, "orderId");

        final List<OrderEvent> orderEvents = getAllOrderEvents(ctx, orderId);
        orderEvents.sort(Comparator.comparingLong(OrderEvent::getTimestamp));
        final Map<String, OrderEvent> eventsByType = getRequiredEventsByType(orderId, orderEvents);
        final OrderEvent placedEvent = eventsByType.get(ORDER_PLACED);
        final OrderEvent pickedEvent = eventsByType.get(ORDER_PICKED);
        final OrderEvent packedEvent = eventsByType.get(ORDER_PACKED);
        final OrderEvent dispatchedEvent = eventsByType.get(ORDER_DISPATCHED);
        final OrderEvent deliveredEvent = eventsByType.get(ORDER_DELIVERED);

        final long pickingDurationMillis = calculateDuration(placedEvent, pickedEvent, ORDER_PICKED, ORDER_PLACED);
        final long packingDurationMillis = calculateDuration(pickedEvent, packedEvent, ORDER_PACKED, ORDER_PICKED);
        final long dispatchDurationMillis =
                calculateDuration(packedEvent, dispatchedEvent, ORDER_DISPATCHED, ORDER_PACKED);
        final long deliveryDurationMillis =
                calculateDuration(placedEvent, deliveredEvent, ORDER_DELIVERED, ORDER_PLACED);

        final List<String> violations = new ArrayList<>();
        if (pickingDurationMillis > PICKING_SLA_MILLIS) {
            violations.add(PICKING_SLA_BREACH);
        }
        if (packingDurationMillis > PACKING_SLA_MILLIS) {
            violations.add(PACKING_SLA_BREACH);
        }
        if (dispatchDurationMillis > DISPATCH_SLA_MILLIS) {
            violations.add(DISPATCH_SLA_BREACH);
        }
        if (deliveryDurationMillis > DELIVERY_SLA_MILLIS) {
            violations.add(DELIVERY_SLA_BREACH);
        }

        final boolean slaSatisfied = violations.isEmpty();
        final String violationType = determineViolationType(violations);
        final SLAResult result = new SLAResult(orderId, pickingDurationMillis, packingDurationMillis,
                dispatchDurationMillis, deliveryDurationMillis, slaSatisfied, violationType);

        if (!result.isSlaSatisfied()) {
            persistViolation(ctx, result, orderEvents);
        }

        return result;
    }

    private OrderEvent recordOrderEvent(final Context ctx, final String orderId, final String storeId,
            final long timestamp, final String eventType) {
        validateRequired(orderId, "orderId");
        validateRequired(storeId, "storeId");

        if (timestamp <= 0L) {
            throw new ChaincodeException("timestamp must be a positive epoch value");
        }

        final ChaincodeStub stub = ctx.getStub();
        final String eventKey = eventCompositeKey(stub, orderId, eventType).toString();
        final String existingState = stub.getStringState(eventKey);
        if (existingState != null && !existingState.isBlank()) {
            throw new ChaincodeException(String.format("Event %s already exists for order %s", eventType, orderId));
        }

        final OrderEvent orderEvent = new OrderEvent(orderId, eventType, timestamp, storeId);
        stub.putStringState(eventKey, orderEvent.toJson());
        return orderEvent;
    }

    private List<OrderEvent> getAllOrderEvents(final Context ctx, final String orderId) {
        final List<OrderEvent> events = new ArrayList<>();
        final ChaincodeStub stub = ctx.getStub();
        QueryResultsIterator<KeyValue> iterator = null;

        try {
            iterator = stub.getStateByPartialCompositeKey(EVENT_OBJECT_TYPE, orderId);
            for (KeyValue entry : iterator) {
                events.add(OrderEvent.fromJson(entry.getStringValue()));
            }
        } catch (Exception e) {
            throw new ChaincodeException("Failed to query order history for order " + orderId, e);
        } finally {
            if (iterator != null) {
                try {
                    iterator.close();
                } catch (Exception e) {
                    throw new ChaincodeException("Failed to close order history iterator for order " + orderId, e);
                }
            }
        }

        return events;
    }

    private Map<String, OrderEvent> getRequiredEventsByType(final Context ctx, final String orderId) {
        final List<OrderEvent> events = getAllOrderEvents(ctx, orderId);
        return getRequiredEventsByType(orderId, events);
    }

    private Map<String, OrderEvent> getRequiredEventsByType(final String orderId, final List<OrderEvent> events) {
        final Map<String, OrderEvent> eventsByType = new LinkedHashMap<>();

        for (OrderEvent event : events) {
            eventsByType.put(event.getEventType(), event);
        }

        requireEvent(eventsByType, orderId, ORDER_PLACED);
        requireEvent(eventsByType, orderId, ORDER_PICKED);
        requireEvent(eventsByType, orderId, ORDER_PACKED);
        requireEvent(eventsByType, orderId, ORDER_DISPATCHED);
        requireEvent(eventsByType, orderId, ORDER_DELIVERED);

        return eventsByType;
    }

    private void requireEvent(final Map<String, OrderEvent> eventsByType, final String orderId, final String eventType) {
        if (!eventsByType.containsKey(eventType)) {
            throw new ChaincodeException(String.format("Required event %s was not found for order %s", eventType,
                    orderId));
        }
    }

    private long calculateDuration(final OrderEvent startEvent, final OrderEvent endEvent, final String endEventType,
            final String startEventType) {
        final long duration = endEvent.getTimestamp() - startEvent.getTimestamp();
        if (duration < 0L) {
            throw new ChaincodeException(String.format("%s timestamp cannot be earlier than %s", endEventType,
                    startEventType));
        }
        return duration;
    }

    private String determineViolationType(final List<String> violations) {
        if (violations.isEmpty()) {
            return NO_VIOLATION;
        }
        return String.join(",", violations);
    }

    private List<ViolationRecord> getViolationRecords(final Context ctx, final String orderId) {
        final List<ViolationRecord> violations = new ArrayList<>();
        final ChaincodeStub stub = ctx.getStub();
        QueryResultsIterator<KeyValue> iterator = null;

        try {
            if (orderId == null || orderId.isBlank()) {
                iterator = stub.getStateByPartialCompositeKey(VIOLATION_OBJECT_TYPE);
            } else {
                iterator = stub.getStateByPartialCompositeKey(VIOLATION_OBJECT_TYPE, orderId);
            }

            for (KeyValue entry : iterator) {
                violations.add(ViolationRecord.fromJson(entry.getStringValue()));
            }
        } catch (Exception e) {
            throw new ChaincodeException("Failed to query SLA violation records", e);
        } finally {
            if (iterator != null) {
                try {
                    iterator.close();
                } catch (Exception e) {
                    throw new ChaincodeException("Failed to close SLA violation iterator", e);
                }
            }
        }

        violations.sort(Comparator.comparingLong(ViolationRecord::getRecordedAtMillis));
        return violations;
    }

    private void persistViolation(final Context ctx, final SLAResult result, final List<OrderEvent> orderEvents) {
        final ChaincodeStub stub = ctx.getStub();
        final String violationKey = violationCompositeKey(stub, result.getOrderId(), result.getViolationType())
                .toString();
        final ViolationRecord violationRecord = new ViolationRecord(result.getOrderId(), result.getViolationType(),
                stub.getTxId(), toEpochMillis(stub.getTxTimestamp()), result, orderEvents.toArray(new OrderEvent[0]));
        final String payload = violationRecord.toJson();

        stub.putStringState(violationKey, payload);
        stub.setEvent(SLA_VIOLATION_EVENT, payload.getBytes(StandardCharsets.UTF_8));
    }

    private CompositeKey eventCompositeKey(final ChaincodeStub stub, final String orderId, final String eventType) {
        return stub.createCompositeKey(EVENT_OBJECT_TYPE, orderId, eventType);
    }

    private CompositeKey violationCompositeKey(final ChaincodeStub stub, final String orderId,
            final String violationType) {
        return stub.createCompositeKey(VIOLATION_OBJECT_TYPE, orderId, violationType);
    }

    private long toEpochMillis(final Instant timestamp) {
        return timestamp.toEpochMilli();
    }

    private void validateRequired(final String value, final String fieldName) {
        if (value == null || value.isBlank()) {
            throw new ChaincodeException(fieldName + " is required");
        }
    }
}
