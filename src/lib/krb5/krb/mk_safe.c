/*
 * lib/krb5/krb/mk_safe.c
 *
 * Copyright 1990,1991 by the Massachusetts Institute of Technology.
 * All Rights Reserved.
 *
 * Export of this software from the United States of America may
 *   require a specific license from the United States Government.
 *   It is the responsibility of any person or organization contemplating
 *   export to obtain such a license before exporting.
 * 
 * WITHIN THAT CONSTRAINT, permission to use, copy, modify, and
 * distribute this software and its documentation for any purpose and
 * without fee is hereby granted, provided that the above copyright
 * notice appear in all copies and that both that copyright notice and
 * this permission notice appear in supporting documentation, and that
 * the name of M.I.T. not be used in advertising or publicity pertaining
 * to distribution of the software without specific, written prior
 * permission.  M.I.T. makes no representations about the suitability of
 * this software for any purpose.  It is provided "as is" without express
 * or implied warranty.
 * 
 *
 * krb5_mk_safe()
 */


#include <krb5/krb5.h>
#include <krb5/asn1.h>
#include <krb5/los-proto.h>
#include <krb5/ext-proto.h>

/*
 Formats a KRB_SAFE message into outbuf.

 userdata is formatted as the user data in the message.
 sumtype specifies the encryption type; key specifies the key which
 might be used to seed the checksum; sender_addr and recv_addr specify
 the full addresses (host and port) of the sender and receiver.
 The host portion of sender_addr is used to form the addresses used in the
 KRB_SAFE message.

 The outbuf buffer storage is allocated, and should be freed by the
 caller when finished.

 returns system errors
*/
krb5_error_code INTERFACE
krb5_mk_safe(context, userdata, sumtype, key, sender_addr, recv_addr,
	     seq_number, safe_flags, rcache, outbuf)
    krb5_context context;
    const krb5_data * userdata;
    const krb5_cksumtype sumtype;
    const krb5_keyblock * key;
    const krb5_address * sender_addr;
    const krb5_address * recv_addr;
    krb5_int32 seq_number;
    krb5_int32 safe_flags;
    krb5_rcache rcache;
    krb5_data * outbuf;
{
    krb5_error_code retval;
    krb5_safe safemsg;
    krb5_octet zero_octet = 0;
    krb5_checksum safe_checksum;
    krb5_data *scratch;

    if (!valid_cksumtype(sumtype))
	return KRB5_PROG_SUMTYPE_NOSUPP;
    if (!is_coll_proof_cksum(sumtype) || !is_keyed_cksum(sumtype))
	return KRB5KRB_AP_ERR_INAPP_CKSUM;

    safemsg.user_data = *userdata;
    safemsg.s_address = (krb5_address *)sender_addr;
    if (recv_addr)
	safemsg.r_address = (krb5_address *)recv_addr;
    else
	safemsg.r_address = 0;

    if (!(safe_flags & KRB5_SAFE_NOTIME)) {
	if (!rcache)
	    /* gotta provide an rcache in this case... */
	    return KRB5_RC_REQUIRED;
	if (retval = krb5_us_timeofday(context, &safemsg.timestamp, &safemsg.usec))
	    return retval;
    } else
	safemsg.timestamp = 0, safemsg.usec = 0;
    if (safe_flags & KRB5_SAFE_DOSEQUENCE) {
	safemsg.seq_number = seq_number;
     } else
	 safemsg.seq_number = 0;
    
    /* to do the checksum stuff, we need to encode the message with a
       zero-length zero-type checksum, then checksum the encoding, then
       re-encode with the 
       checksum. */

    safe_checksum.checksum_type = 0;
    safe_checksum.length = 0;
    safe_checksum.contents = &zero_octet;

    safemsg.checksum = &safe_checksum;

    if (retval = encode_krb5_safe(&safemsg, &scratch))
	return retval;

#define clean_scratch() {(void) memset((char *)scratch->data, 0,\
				       scratch->length); \
			  krb5_free_data(context, scratch);}
			 
    if (!(safe_checksum.contents =
	  (krb5_octet *) malloc(krb5_checksum_size(context, sumtype)))) {
	clean_scratch();
	return ENOMEM;
    }
    if (retval = krb5_calculate_checksum(context, sumtype, scratch->data,
					 scratch->length,
					 (krb5_pointer) key->contents,
					 key->length, &safe_checksum)) {
	krb5_xfree(safe_checksum.contents);
	clean_scratch();
	return retval;
    }
    safemsg.checksum = &safe_checksum;
    clean_scratch();
    if (retval = encode_krb5_safe(&safemsg, &scratch)) {
	krb5_xfree(safe_checksum.contents);
	return retval;
    }
    krb5_xfree(safe_checksum.contents);
    if (!(safe_flags & KRB5_SAFE_NOTIME)) {
	krb5_donot_replay replay;

	if (retval = krb5_gen_replay_name(context, sender_addr, "_safe",
					  &replay.client)) {
	    clean_scratch();
	    return retval;
	}

	replay.server = "";		/* XXX */
	replay.cusec = safemsg.usec;
	replay.ctime = safemsg.timestamp;
	if (retval = krb5_rc_store(context, rcache, &replay)) {
	    /* should we really error out here? XXX */
	    clean_scratch();
	    krb5_xfree(replay.client);
	    return retval;
	}
	krb5_xfree(replay.client);
    }
    *outbuf = *scratch;
    krb5_xfree(scratch);

    return 0;
}

