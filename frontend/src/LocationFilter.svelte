<script>
    import Icon from "@iconify/svelte";

    /**
     * @typedef {Object} Props
     * @property {any} locations
     * @property {any} [selected_location]
     */

    /** @type {Props} */
    let { locations, selected_location = $bindable(null) } = $props();
</script>

<div>
    <Icon icon="mdi:location" width="20" height="20" />
    {#each locations as location}
        <button
            onclick={() => (selected_location = location)}
            class:selected={selected_location === location}>{location}</button
        >
    {/each}
</div>

<style>
    div {
        display: flex;
        margin-bottom: 10px;
        margin-top: 10px;
    }

    button:first-of-type {
        border-left: 1px solid var(--theme-color);
        border-radius: 5px 0 0 5px;
    }

    button:last-of-type {
        border-radius: 0 5px 5px 0;
    }

    button {
        box-sizing: border-box;
        margin: 0;
        border: 1px solid var(--theme-color);
        border-left: 0px;
        cursor: pointer;
        display: inline;
        color: var(--theme-color);
        background: transparent;
    }

    button.selected {
        background: var(--theme-color);
        color: var(--theme-color-selected);
    }
</style>
