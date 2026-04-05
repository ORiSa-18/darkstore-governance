package org.example;

import com.owlike.genson.Genson;
import org.hyperledger.fabric.contract.annotation.DataType;
import org.hyperledger.fabric.contract.annotation.Property;

@DataType
public final class SLAResult {

    private static final Genson GENSON = new Genson();

    @Property
    private String orderId;

    @Property
    private boolean slaSatisfied;

    @Property
    private String violationType;

    @Property
    private long pickingDurationMillis;

    @Property
    private long packingDurationMillis;

    @Property
    private long dispatchDurationMillis;

    @Property
    private long deliveryDurationMillis;

    public SLAResult() {
    }

    public SLAResult(final String orderId, final long pickingDurationMillis, final long packingDurationMillis,
            final long dispatchDurationMillis, final long deliveryDurationMillis, final boolean slaSatisfied,
            final String violationType) {
        this.orderId = orderId;
        this.pickingDurationMillis = pickingDurationMillis;
        this.packingDurationMillis = packingDurationMillis;
        this.dispatchDurationMillis = dispatchDurationMillis;
        this.deliveryDurationMillis = deliveryDurationMillis;
        this.slaSatisfied = slaSatisfied;
        this.violationType = violationType;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(final String orderId) {
        this.orderId = orderId;
    }

    public boolean isSlaSatisfied() {
        return slaSatisfied;
    }

    public void setSlaSatisfied(final boolean slaSatisfied) {
        this.slaSatisfied = slaSatisfied;
    }

    public String getViolationType() {
        return violationType;
    }

    public void setViolationType(final String violationType) {
        this.violationType = violationType;
    }

    public long getPickingDurationMillis() {
        return pickingDurationMillis;
    }

    public void setPickingDurationMillis(final long pickingDurationMillis) {
        this.pickingDurationMillis = pickingDurationMillis;
    }

    public long getPackingDurationMillis() {
        return packingDurationMillis;
    }

    public void setPackingDurationMillis(final long packingDurationMillis) {
        this.packingDurationMillis = packingDurationMillis;
    }

    public long getDispatchDurationMillis() {
        return dispatchDurationMillis;
    }

    public void setDispatchDurationMillis(final long dispatchDurationMillis) {
        this.dispatchDurationMillis = dispatchDurationMillis;
    }

    public long getDeliveryDurationMillis() {
        return deliveryDurationMillis;
    }

    public void setDeliveryDurationMillis(final long deliveryDurationMillis) {
        this.deliveryDurationMillis = deliveryDurationMillis;
    }

    public String toJson() {
        return GENSON.serialize(this);
    }

    public static SLAResult fromJson(final String json) {
        return GENSON.deserialize(json, SLAResult.class);
    }
}
