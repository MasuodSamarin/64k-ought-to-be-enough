; Invite intro for Flashparty 2018
; Pungas de Villa Martelli - http://pungas.space
;
; code: riq (http://retro.moe)

bits    16
cpu     8086


;extern irq_8_cleanup, irq_8_init
;extern wait_vertical_retrace
extern dzx7_speed, dzx7_size

;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
; MACROS
;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;

;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
;
; CODE
;
;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
main:
        resb    0x100                           ;cannot use "org 0x100" when using multiple .o files

        mov     ax,0x0009                       ;320x200 16 colors
        int     0x10

        mov     ax,cs
        mov     ds,ax
        mov     si,image1                       ;ds:si source

        mov     ax,0x1800
        mov     es,ax
        sub     di,di                           ;es:di destination

        call    dzx7_speed

        call    scroll_anim


        sub     ax,ax
        int     0x16                            ;wait key
        int     0x19                            ;reboot

        ret


;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
scroll_anim:
        ret

;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
;DATA
;=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-;
image1:
        incbin 'part2/image1.bin.zx7'

charset:
        incbin 'part2/charset_0x00_0x40.bin'

scroll_text:
        db 'HOLA HOLA, ESTO ES UNA PRUEBA DE SCROLL'
        db 0
