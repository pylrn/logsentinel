const REPLAY_ENVIRONMENTS = {
  hdfs: {
    label: "HDFS cloud storage",
    provenance: "Public HDFS-shaped demonstration",
    status: "illustrative",
    events: [
      {time:"10:03:14", title:"Block received", template:"Receiving block <BLOCK_ID> from <IP>", score:.09, components:{Rarity:.02, Sequence:.03, Volume:.04}, expected:["Verifying checksum", "Packet responder registered"], explanation:"This follows the ordinary block-receive pattern."},
      {time:"10:03:18", title:"Missing responder", template:"PacketResponder <BLOCK_ID> has no downstream peer", score:.84, components:{Rarity:.30, Sequence:.38, Volume:.16}, expected:["Verifying checksum", "Block finalized"], explanation:"The expected completion was replaced by a rare responder failure."},
      {time:"10:03:21", title:"Retry scheduled", template:"Retrying write pipeline for <BLOCK_ID>", score:.61, components:{Rarity:.21, Sequence:.22, Volume:.18}, expected:["Block finalized"], explanation:"A retry is unusual after this short sequence, but needs host context."}
    ]
  },
  bgl: {
    label: "BGL supercomputing",
    provenance: "Public BGL-shaped demonstration",
    status: "illustrative",
    events: [
      {time:"14:20:01", title:"Node heartbeat", template:"Node <HOST_ID> heartbeat accepted", score:.08, components:{Rarity:.01, Sequence:.03, Volume:.04}, expected:["Node heartbeat accepted"], explanation:"Routine heartbeat traffic."},
      {time:"14:20:04", title:"ECC correction", template:"Correctable ECC event on <HOST_ID>", score:.48, components:{Rarity:.20, Sequence:.12, Volume:.16}, expected:["Node heartbeat accepted"], explanation:"A single corrected event may be normal; track recurrence."},
      {time:"14:20:06", title:"Repeated hardware event", template:"ECC event burst on <HOST_ID>", score:.79, components:{Rarity:.28, Sequence:.19, Volume:.32}, expected:["Node heartbeat accepted", "Job progress recorded"], explanation:"The event-rate signal dominates this illustrative alert."}
    ]
  },
  "security-demo": {
    label: "Security telemetry",
    provenance: "Synthetic redacted security demonstration",
    status: "illustrative",
    events: [
      {time:"09:44:12", title:"Login accepted", template:"sshd: accepted password for <USER_ID> from <IP>", score:.07, components:{Rarity:.02, Sequence:.03, Volume:.02}, expected:["Session opened"], explanation:"Routine authentication event."},
      {time:"09:44:25", title:"Authentication burst", template:"sshd: PAM <*> authentication failures from <IP> for <USER_ID>", score:.87, components:{Rarity:.27, Sequence:.34, Volume:.26}, expected:["Session opened", "Session closed"], explanation:"Repeated failures break the expected session path. Validate rate limits and host context before escalation."},
      {time:"09:44:31", title:"Connection closed", template:"sshd: connection closed for <USER_ID>", score:.33, components:{Rarity:.08, Sequence:.14, Volume:.11}, expected:["Session closed"], explanation:"The normal close event reduces the ongoing sequence concern."}
    ]
  }
};
