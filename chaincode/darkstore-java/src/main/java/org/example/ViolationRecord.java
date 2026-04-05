package org.example;

import com.owlike.genson.Genson;
import org.hyperledger.fabric.contract.annotation.DataType;
import org.hyperledger.fabric.contract.annotation.Property;

@DataType
public final class ViolationRecord {

    private static final Genson GENSON = new Genson();

    @Property
    private String orderId;

    @Property
    private String violationType;

    @Property
    private String verificationTransactionId;

    @Property
    private long recordedAtMillis;

    @Property
    private SLAResult slaResult;

    @Property
    private OrderEvent[] orderEvents;

    public ViolationRecord() {
    }

    public ViolationRecord(final String orderId, final String violationType, final String verificationTransactionId,
            final long recordedAtMillis, final SLAResult slaResult, final OrderEvent[] orderEvents) {
        this.orderId = orderId;
        this.violationType = violationType;
        this.verificationTransactionId = verificationTransactionId;
        this.recordedAtMillis = recordedAtMillis;
        this.slaResult = slaResult;
        this.orderEvents = orderEvents;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(final String orderId) {
        this.orderId = orderId;
    }

    public String getViolationType() {
        return violationType;
    }

    public void setViolationType(final String violationType) {
        this.violationType = violationType;
    }

    public String getVerificationTransactionId() {
        return verificationTransactionId;
    }

    public void setVerificationTransactionId(final String verificationTransactionId) {
        this.verificationTransactionId = verificationTransactionId;
    }

    public long getRecordedAtMillis() {
        return recordedAtMillis;
    }

    public void setRecordedAtMillis(final long recordedAtMillis) {
        this.recordedAtMillis = recordedAtMillis;
    }

    public SLAResult getSlaResult() {
        return slaResult;
    }

    public void setSlaResult(final SLAResult slaResult) {
        this.slaResult = slaResult;
    }

    public OrderEvent[] getOrderEvents() {
        return orderEvents;
    }

    public void setOrderEvents(final OrderEvent[] orderEvents) {
        this.orderEvents = orderEvents;
    }

    public String toJson() {
        return GENSON.serialize(this);
    }

    public static ViolationRecord fromJson(final String json) {
        return GENSON.deserialize(json, ViolationRecord.class);
    }
}
