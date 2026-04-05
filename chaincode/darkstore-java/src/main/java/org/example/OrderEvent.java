package org.example;

import com.owlike.genson.Genson;
import org.hyperledger.fabric.contract.annotation.DataType;
import org.hyperledger.fabric.contract.annotation.Property;

@DataType
public final class OrderEvent {

    private static final Genson GENSON = new Genson();

    @Property
    private String orderId;

    @Property
    private String eventType;

    @Property
    private long timestamp;

    @Property
    private String storeId;

    public OrderEvent() {
    }

    public OrderEvent(final String orderId, final String eventType, final long timestamp, final String storeId) {
        this.orderId = orderId;
        this.eventType = eventType;
        this.timestamp = timestamp;
        this.storeId = storeId;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(final String orderId) {
        this.orderId = orderId;
    }

    public String getEventType() {
        return eventType;
    }

    public void setEventType(final String eventType) {
        this.eventType = eventType;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(final long timestamp) {
        this.timestamp = timestamp;
    }

    public String getStoreId() {
        return storeId;
    }

    public void setStoreId(final String storeId) {
        this.storeId = storeId;
    }

    public String toJson() {
        return GENSON.serialize(this);
    }

    public static OrderEvent fromJson(final String json) {
        return GENSON.deserialize(json, OrderEvent.class);
    }
}
